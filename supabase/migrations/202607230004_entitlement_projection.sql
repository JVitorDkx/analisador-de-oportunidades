begin;

create or replace view public.tenant_entitlements
with (security_invoker = true, security_barrier = true)
as
select tenant.id as tenant_id,
       entitlement.tier,
       entitlement.monthly_analysis_limit,
       entitlement.history_retention_days
  from public.tenants as tenant
 cross join lateral private.tenant_entitlement(tenant.id) as entitlement;

revoke all on table public.tenant_entitlements from public;
revoke all on table public.tenant_entitlements from anon, authenticated;

grant select (
    tenant_id,
    tier,
    monthly_analysis_limit,
    history_retention_days
) on table public.tenant_entitlements to authenticated;

comment on view public.tenant_entitlements is
    'Read-only security-invoker projection of the effective server-side plan for authorized tenant members.';

commit;
