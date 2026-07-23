begin;

create or replace function public.list_tenant_analyses(
    target_tenant_id uuid,
    target_limit integer default 20,
    target_offset integer default 0
)
returns table (
    id uuid,
    client_analysis_id text,
    analysis_mode text,
    input_status text,
    recommendation text,
    confidence text,
    recommended_opportunity_id text,
    official_score numeric,
    executive_summary text,
    processed_at timestamptz,
    created_at timestamptz,
    total_count bigint
)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    retention_days integer;
begin
    if auth.uid() is null or not private.is_tenant_member(target_tenant_id) then
        raise exception 'tenant history unavailable' using errcode = '42501';
    end if;
    if target_limit < 1 or target_limit > 100 or target_offset < 0 then
        raise exception 'invalid pagination' using errcode = '22023';
    end if;

    select entitlement.history_retention_days
      into retention_days
      from private.tenant_entitlement(target_tenant_id) as entitlement;

    return query
    select analysis.id,
           analysis.client_analysis_id,
           analysis.analysis_mode,
           analysis.input_status,
           analysis.recommendation,
           analysis.confidence,
           analysis.recommended_opportunity_id,
           analysis.official_score,
           analysis.executive_summary,
           analysis.processed_at,
           analysis.created_at,
           count(*) over () as total_count
      from public.analyses as analysis
     where analysis.tenant_id = target_tenant_id
       and (
           retention_days is null
           or analysis.created_at >= now() - make_interval(days => retention_days)
       )
     order by analysis.created_at desc, analysis.id desc
     limit target_limit
    offset target_offset;
end;
$$;

create or replace function public.get_tenant_analysis(
    target_tenant_id uuid,
    target_analysis_id uuid
)
returns table (
    id uuid,
    tenant_id uuid,
    created_at timestamptz,
    result_payload jsonb
)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    retention_days integer;
begin
    if auth.uid() is null or not private.is_tenant_member(target_tenant_id) then
        raise exception 'tenant analysis unavailable' using errcode = '42501';
    end if;

    select entitlement.history_retention_days
      into retention_days
      from private.tenant_entitlement(target_tenant_id) as entitlement;

    return query
    select analysis.id,
           analysis.tenant_id,
           analysis.created_at,
           analysis.result_payload
      from public.analyses as analysis
     where analysis.tenant_id = target_tenant_id
       and analysis.id = target_analysis_id
       and (
           retention_days is null
           or analysis.created_at >= now() - make_interval(days => retention_days)
       )
     limit 1;
end;
$$;

create or replace function public.get_tenant_dashboard(
    target_tenant_id uuid
)
returns table (
    tier text,
    monthly_limit integer,
    quota_used integer,
    quota_remaining integer,
    total_analyses bigint,
    scored_analyses bigint,
    average_official_score numeric,
    sufficient_analyses bigint,
    insufficient_analyses bigint,
    rejected_analyses bigint,
    recommendation_counts jsonb
)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    entitlement record;
    used_units integer;
begin
    if auth.uid() is null or not private.is_tenant_member(target_tenant_id) then
        raise exception 'tenant dashboard unavailable' using errcode = '42501';
    end if;

    select effective.*
      into entitlement
      from private.tenant_entitlement(target_tenant_id) as effective;

    select coalesce(sum(ledger.units), 0)::integer
      into used_units
      from public.analysis_quota_ledger as ledger
     where ledger.tenant_id = target_tenant_id
       and ledger.period_start = date_trunc('month', now())::date
       and ledger.status in ('reserved', 'consumed');

    return query
    with visible as (
        select analysis.*
          from public.analyses as analysis
         where analysis.tenant_id = target_tenant_id
           and (
               entitlement.history_retention_days is null
               or analysis.created_at >=
                  now() - make_interval(days => entitlement.history_retention_days)
           )
    ),
    counts as (
        select visible.recommendation, count(*)::bigint as amount
          from visible
         group by visible.recommendation
    )
    select entitlement.tier,
           entitlement.monthly_analysis_limit,
           used_units,
           greatest(entitlement.monthly_analysis_limit - used_units, 0),
           count(*)::bigint,
           count(visible.official_score)::bigint,
           round(avg(visible.official_score), 2),
           count(*) filter (where visible.input_status = 'sufficient')::bigint,
           count(*) filter (where visible.input_status = 'insufficient')::bigint,
           count(*) filter (where visible.recommendation = 'reject_for_now')::bigint,
           coalesce(
               (select jsonb_object_agg(counts.recommendation, counts.amount) from counts),
               '{}'::jsonb
           )
      from visible;
end;
$$;

revoke all on function public.list_tenant_analyses(uuid, integer, integer) from public, anon;
revoke all on function public.get_tenant_analysis(uuid, uuid) from public, anon;
revoke all on function public.get_tenant_dashboard(uuid) from public, anon;
grant execute on function public.list_tenant_analyses(uuid, integer, integer) to authenticated;
grant execute on function public.get_tenant_analysis(uuid, uuid) to authenticated;
grant execute on function public.get_tenant_dashboard(uuid) to authenticated;

comment on function public.list_tenant_analyses(uuid, integer, integer) is
    'RLS-bound, retention-aware tenant analysis history.';
comment on function public.get_tenant_analysis(uuid, uuid) is
    'RLS-bound, retention-aware validated analysis detail.';
comment on function public.get_tenant_dashboard(uuid) is
    'Server-computed tenant history and quota aggregates.';

commit;
