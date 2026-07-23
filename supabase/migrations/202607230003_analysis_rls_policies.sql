begin;

alter table public.billing_plans enable row level security;
alter table public.billing_plans force row level security;
alter table public.analyses enable row level security;
alter table public.analyses force row level security;
alter table public.analysis_advanced_details enable row level security;
alter table public.analysis_advanced_details force row level security;
alter table public.analysis_quota_ledger enable row level security;
alter table public.analysis_quota_ledger force row level security;

revoke all on table public.billing_plans from anon, authenticated;
revoke all on table public.analyses from anon, authenticated;
revoke all on table public.analysis_advanced_details from anon, authenticated;
revoke all on table public.analysis_quota_ledger from anon, authenticated;

grant select (
    plan_id,
    tier,
    monthly_analysis_limit,
    history_retention_days
) on table public.billing_plans to authenticated;

grant select (
    id,
    tenant_id,
    parent_analysis_id,
    client_analysis_id,
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
    processed_at,
    created_at
) on table public.analyses to authenticated;

grant select (
    analysis_id,
    tenant_id,
    payload,
    created_at
) on table public.analysis_advanced_details to authenticated;

grant select (
    id,
    tenant_id,
    user_id,
    analysis_id,
    period_start,
    units,
    status,
    created_at,
    finalized_at
) on table public.analysis_quota_ledger to authenticated;

drop policy if exists billing_plans_select_active on public.billing_plans;
create policy billing_plans_select_active
on public.billing_plans for select
to authenticated
using (is_active);

drop policy if exists analyses_select_member on public.analyses;
create policy analyses_select_member
on public.analyses for select
to authenticated
using (private.is_tenant_member(tenant_id));

drop policy if exists analysis_advanced_details_select_pro on public.analysis_advanced_details;
create policy analysis_advanced_details_select_pro
on public.analysis_advanced_details for select
to authenticated
using (
    private.is_tenant_member(tenant_id)
    and exists (
        select 1
          from private.tenant_entitlement(tenant_id) as entitlement
         where entitlement.tier = 'pro'
    )
);

drop policy if exists analysis_quota_ledger_select_member on public.analysis_quota_ledger;
create policy analysis_quota_ledger_select_member
on public.analysis_quota_ledger for select
to authenticated
using (private.is_tenant_member(tenant_id));

comment on policy analysis_advanced_details_select_pro on public.analysis_advanced_details is
    'Advanced payload is absent from Free tenant query results at the database boundary.';
comment on policy analysis_quota_ledger_select_member on public.analysis_quota_ledger is
    'Tenant members may inspect usage but cannot mutate the server-managed ledger directly.';

commit;
