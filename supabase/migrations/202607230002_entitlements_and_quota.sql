begin;

create table if not exists public.analysis_quota_ledger (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references public.tenants (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete restrict,
    analysis_id uuid,
    idempotency_key text not null,
    period_start date not null,
    units integer not null default 1,
    status text not null default 'reserved',
    created_at timestamptz not null default now(),
    finalized_at timestamptz,
    constraint analysis_quota_ledger_tenant_analysis_fk
        foreign key (tenant_id, analysis_id)
        references public.analyses (tenant_id, id)
        on delete restrict,
    constraint analysis_quota_ledger_tenant_idempotency_unique
        unique (tenant_id, idempotency_key),
    constraint analysis_quota_ledger_idempotency_key_length
        check (char_length(btrim(idempotency_key)) between 8 and 128),
    constraint analysis_quota_ledger_units
        check (units > 0),
    constraint analysis_quota_ledger_status
        check (status in ('reserved', 'consumed', 'released')),
    constraint analysis_quota_ledger_finalization
        check (
            (status = 'reserved' and finalized_at is null and analysis_id is null)
            or (status = 'consumed' and finalized_at is not null and analysis_id is not null)
            or (status = 'released' and finalized_at is not null and analysis_id is null)
        )
);

create unique index if not exists analysis_quota_ledger_analysis_uidx
    on public.analysis_quota_ledger (analysis_id)
    where analysis_id is not null;

create index if not exists analysis_quota_ledger_usage_idx
    on public.analysis_quota_ledger (tenant_id, period_start, status);

create index if not exists analysis_quota_ledger_user_idx
    on public.analysis_quota_ledger (user_id, tenant_id, created_at desc);

create or replace function private.tenant_entitlement(
    target_tenant_id uuid
)
returns table (
    tier text,
    monthly_analysis_limit integer,
    history_retention_days integer
)
language sql
stable
security definer
set search_path = ''
as $$
    with authorized_tenant as (
        select private.is_tenant_member(target_tenant_id) as is_member
    ),
    active_subscription as (
        select plan.tier,
               plan.monthly_analysis_limit,
               plan.history_retention_days
          from public.subscriptions as subscription
          join public.billing_plans as plan
            on plan.plan_id = subscription.plan_id
          cross join authorized_tenant as authorization
         where subscription.tenant_id = target_tenant_id
           and authorization.is_member
           and subscription.status in ('trialing', 'active')
           and (
               subscription.current_period_end is null
               or subscription.current_period_end > now()
           )
           and plan.is_active
         limit 1
    ),
    free_fallback as (
        select plan.tier,
               plan.monthly_analysis_limit,
               plan.history_retention_days
          from public.billing_plans as plan
         cross join authorized_tenant as authorization
         where plan.plan_id = 'free'
           and plan.is_active
           and authorization.is_member
         limit 1
    )
    select entitlement.tier,
           entitlement.monthly_analysis_limit,
           entitlement.history_retention_days
      from (
          select active.tier,
                 active.monthly_analysis_limit,
                 active.history_retention_days,
                 0 as priority
            from active_subscription as active
          union all
          select fallback.tier,
                 fallback.monthly_analysis_limit,
                 fallback.history_retention_days,
                 1 as priority
            from free_fallback as fallback
      ) as entitlement
     order by entitlement.priority
     limit 1;
$$;

create or replace function private.reserve_analysis_quota(
    target_tenant_id uuid,
    target_idempotency_key text
)
returns table (
    reservation_id uuid,
    tier text,
    monthly_limit integer,
    used integer,
    remaining integer,
    already_reserved boolean,
    reservation_status text,
    linked_analysis_id uuid
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    current_period date := date_trunc('month', now())::date;
    resolved_tier text;
    resolved_limit integer;
    existing_reservation public.analysis_quota_ledger%rowtype;
    current_usage integer;
    new_reservation_id uuid;
begin
    if auth.uid() is null
       or not exists (
           select 1
             from public.tenant_memberships as membership
            where membership.tenant_id = target_tenant_id
              and membership.user_id = auth.uid()
       ) then
        raise exception 'tenant access denied' using errcode = '42501';
    end if;

    if target_idempotency_key is null
       or char_length(btrim(target_idempotency_key)) not between 8 and 128 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;

    perform pg_advisory_xact_lock(
        hashtextextended(target_tenant_id::text || ':' || current_period::text, 0)
    );

    select ledger.*
      into existing_reservation
      from public.analysis_quota_ledger as ledger
     where ledger.tenant_id = target_tenant_id
       and ledger.idempotency_key = target_idempotency_key;

    select entitlement.tier,
           entitlement.monthly_analysis_limit
      into resolved_tier,
           resolved_limit
      from private.tenant_entitlement(target_tenant_id) as entitlement;

    if resolved_tier is null or resolved_limit is null then
        raise exception 'tenant entitlement unavailable' using errcode = 'P0001';
    end if;

    select coalesce(sum(ledger.units), 0)::integer
      into current_usage
      from public.analysis_quota_ledger as ledger
     where ledger.tenant_id = target_tenant_id
       and ledger.period_start = current_period
       and ledger.status in ('reserved', 'consumed');

    if existing_reservation.id is not null then
        if existing_reservation.user_id <> auth.uid() then
            raise exception 'idempotency key unavailable' using errcode = '42501';
        end if;

        return query
        select existing_reservation.id,
               resolved_tier,
               resolved_limit,
               current_usage,
               greatest(resolved_limit - current_usage, 0),
               true,
               existing_reservation.status,
               existing_reservation.analysis_id;
        return;
    end if;

    if current_usage >= resolved_limit then
        raise exception 'analysis quota exceeded' using errcode = 'P0001';
    end if;

    insert into public.analysis_quota_ledger (
        tenant_id,
        user_id,
        idempotency_key,
        period_start
    )
    values (
        target_tenant_id,
        auth.uid(),
        btrim(target_idempotency_key),
        current_period
    )
    returning id into new_reservation_id;

    current_usage := current_usage + 1;

    return query
    select new_reservation_id,
           resolved_tier,
           resolved_limit,
           current_usage,
           greatest(resolved_limit - current_usage, 0),
           false,
           'reserved'::text,
           null::uuid;
end;
$$;

create or replace function private.finalize_analysis_quota(
    target_tenant_id uuid,
    target_reservation_id uuid,
    target_analysis_id uuid,
    succeeded boolean
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
    reservation public.analysis_quota_ledger%rowtype;
begin
    if auth.uid() is null
       or not exists (
           select 1
             from public.tenant_memberships as membership
            where membership.tenant_id = target_tenant_id
              and membership.user_id = auth.uid()
       ) then
        raise exception 'tenant access denied' using errcode = '42501';
    end if;

    select ledger.*
      into reservation
      from public.analysis_quota_ledger as ledger
     where ledger.id = target_reservation_id
       and ledger.tenant_id = target_tenant_id
       and ledger.user_id = auth.uid()
     for update;

    if reservation.id is null then
        raise exception 'quota reservation not found' using errcode = 'P0002';
    end if;

    if reservation.status <> 'reserved' then
        return;
    end if;

    if succeeded and target_analysis_id is null then
        raise exception 'analysis id is required' using errcode = '22023';
    end if;

    if succeeded is null then
        raise exception 'finalization outcome is required' using errcode = '22023';
    end if;

    update public.analysis_quota_ledger
       set status = case when succeeded then 'consumed' else 'released' end,
           analysis_id = case when succeeded then target_analysis_id else null end,
           finalized_at = now()
     where id = reservation.id;
end;
$$;

revoke all on function private.tenant_entitlement(uuid) from public;
revoke all on function private.reserve_analysis_quota(uuid, text) from public;
revoke all on function private.finalize_analysis_quota(uuid, uuid, uuid, boolean) from public;

grant execute on function private.tenant_entitlement(uuid) to authenticated;
grant execute on function private.reserve_analysis_quota(uuid, text) to authenticated;
grant execute on function private.finalize_analysis_quota(uuid, uuid, uuid, boolean) to authenticated;

comment on table public.analysis_quota_ledger is
    'Append-oriented tenant quota reservations with idempotent monthly consumption.';
comment on function private.reserve_analysis_quota(uuid, text) is
    'Atomically reserves one analysis unit after verifying tenant membership and server-side entitlement.';

commit;
