begin;

create or replace function public.reserve_analysis_quota(
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
    linked_analysis_id uuid,
    stored_result_payload jsonb
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    reservation record;
    current_period date := date_trunc('month', now())::date;
begin
    select quota.*
      into reservation
      from private.reserve_analysis_quota(
          target_tenant_id,
          target_idempotency_key
      ) as quota;

    if reservation.reservation_id is null then
        raise exception 'quota reservation unavailable' using errcode = 'P0001';
    end if;

    if reservation.reservation_status = 'released' then
        if reservation.used >= reservation.monthly_limit then
            raise exception 'analysis quota exceeded' using errcode = 'P0001';
        end if;

        update public.analysis_quota_ledger as ledger
           set period_start = current_period,
               status = 'reserved',
               created_at = now(),
               finalized_at = null,
               analysis_id = null
         where ledger.id = reservation.reservation_id
           and ledger.tenant_id = target_tenant_id
           and ledger.user_id = auth.uid()
           and ledger.status = 'released';

        if not found then
            raise exception 'quota reservation unavailable' using errcode = 'P0001';
        end if;

        reservation.used := reservation.used + 1;
        reservation.remaining := greatest(
            reservation.monthly_limit - reservation.used,
            0
        );
        reservation.already_reserved := false;
        reservation.reservation_status := 'reserved';
        reservation.linked_analysis_id := null;
    end if;

    return query
    select reservation.reservation_id,
           reservation.tier,
           reservation.monthly_limit,
           reservation.used,
           reservation.remaining,
           reservation.already_reserved,
           reservation.reservation_status,
           reservation.linked_analysis_id,
           analysis.result_payload
      from (select 1) as singleton
      left join public.analyses as analysis
        on analysis.id = reservation.linked_analysis_id
       and analysis.tenant_id = target_tenant_id;
end;
$$;

create or replace function public.complete_analysis(
    target_tenant_id uuid,
    target_reservation_id uuid,
    target_client_analysis_id text,
    target_analysis_mode text,
    target_input_status text,
    target_recommendation text,
    target_confidence text,
    target_recommended_opportunity_id text,
    target_official_score numeric,
    target_executive_summary text,
    target_input_schema_version text,
    target_output_schema_version text,
    target_score_version text,
    target_input_payload jsonb,
    target_result_payload jsonb,
    target_processed_at timestamptz
)
returns table (
    analysis_id uuid,
    stored_result_payload jsonb
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    reservation public.analysis_quota_ledger%rowtype;
    stored_analysis_id uuid;
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

    if reservation.status = 'consumed' then
        return query
        select analysis.id,
               analysis.result_payload
          from public.analyses as analysis
         where analysis.id = reservation.analysis_id
           and analysis.tenant_id = target_tenant_id;
        return;
    end if;

    if reservation.status <> 'reserved' then
        raise exception 'quota reservation is not active' using errcode = 'P0001';
    end if;

    if jsonb_typeof(target_input_payload) <> 'object'
       or jsonb_typeof(target_result_payload) <> 'object' then
        raise exception 'analysis payloads must be JSON objects' using errcode = '22023';
    end if;

    if target_input_payload ->> 'analysis_id' <> target_client_analysis_id
       or target_result_payload ->> 'analysis_id' <> target_client_analysis_id
       or target_input_payload ->> 'schema_version' <> target_input_schema_version
       or target_result_payload ->> 'schema_version' <> target_output_schema_version
       or target_result_payload ->> 'analysis_mode' <> target_analysis_mode
       or target_result_payload ->> 'input_status' <> target_input_status
       or target_result_payload ->> 'recommendation' <> target_recommendation
       or target_result_payload ->> 'confidence' <> target_confidence
       or target_result_payload #>> '{versions,score_version}' <> target_score_version then
        raise exception 'analysis payload metadata is inconsistent' using errcode = '22023';
    end if;

    insert into public.analyses (
        tenant_id,
        created_by,
        client_analysis_id,
        idempotency_key,
        analysis_mode,
        input_status,
        recommendation,
        confidence,
        recommended_opportunity_id,
        official_score,
        executive_summary,
        input_schema_version,
        output_schema_version,
        score_version,
        input_payload,
        result_payload,
        processed_at
    )
    values (
        target_tenant_id,
        auth.uid(),
        target_client_analysis_id,
        reservation.idempotency_key,
        target_analysis_mode,
        target_input_status,
        target_recommendation,
        target_confidence,
        target_recommended_opportunity_id,
        target_official_score,
        target_executive_summary,
        target_input_schema_version,
        target_output_schema_version,
        target_score_version,
        target_input_payload,
        target_result_payload,
        target_processed_at
    )
    returning id into stored_analysis_id;

    update public.analysis_quota_ledger as ledger
       set status = 'consumed',
           analysis_id = stored_analysis_id,
           finalized_at = now()
     where ledger.id = reservation.id;

    return query
    select analysis.id,
           analysis.result_payload
      from public.analyses as analysis
     where analysis.id = stored_analysis_id
       and analysis.tenant_id = target_tenant_id;
end;
$$;

create or replace function public.release_analysis_quota(
    target_tenant_id uuid,
    target_reservation_id uuid
)
returns table (
    released boolean
)
language plpgsql
security definer
set search_path = ''
as $$
begin
    perform private.finalize_analysis_quota(
        target_tenant_id,
        target_reservation_id,
        null,
        false
    );

    return query
    select ledger.status = 'released'
      from public.analysis_quota_ledger as ledger
     where ledger.id = target_reservation_id
       and ledger.tenant_id = target_tenant_id
       and ledger.user_id = auth.uid();
end;
$$;

revoke execute on function private.reserve_analysis_quota(uuid, text) from authenticated;
revoke execute on function private.finalize_analysis_quota(uuid, uuid, uuid, boolean)
    from authenticated;

revoke all on function public.reserve_analysis_quota(uuid, text) from public;
revoke all on function public.reserve_analysis_quota(uuid, text) from anon;
revoke all on function public.complete_analysis(
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    text,
    text,
    numeric,
    text,
    text,
    text,
    text,
    jsonb,
    jsonb,
    timestamptz
) from public;
revoke all on function public.complete_analysis(
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    text,
    text,
    numeric,
    text,
    text,
    text,
    text,
    jsonb,
    jsonb,
    timestamptz
) from anon;
revoke all on function public.release_analysis_quota(uuid, uuid) from public;
revoke all on function public.release_analysis_quota(uuid, uuid) from anon;

grant execute on function public.reserve_analysis_quota(uuid, text) to authenticated;
grant execute on function public.complete_analysis(
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    text,
    text,
    numeric,
    text,
    text,
    text,
    text,
    jsonb,
    jsonb,
    timestamptz
) to authenticated;
grant execute on function public.release_analysis_quota(uuid, uuid) to authenticated;

comment on function public.reserve_analysis_quota(uuid, text) is
    'User-JWT-bound idempotent quota reservation exposed through PostgREST.';
comment on function public.complete_analysis(
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    text,
    text,
    numeric,
    text,
    text,
    text,
    text,
    jsonb,
    jsonb,
    timestamptz
) is
    'Atomically persists a validated analysis and consumes its tenant quota reservation.';
comment on function public.release_analysis_quota(uuid, uuid) is
    'Idempotently releases a reservation when deterministic analysis does not complete.';

commit;
