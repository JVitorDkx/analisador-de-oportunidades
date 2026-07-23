begin;

create table if not exists public.billing_plans (
    plan_id text primary key,
    tier text not null,
    monthly_analysis_limit integer not null,
    history_retention_days integer,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint billing_plans_plan_id_format
        check (plan_id ~ '^[a-z0-9][a-z0-9_-]{1,63}$'),
    constraint billing_plans_tier
        check (tier in ('free', 'pro')),
    constraint billing_plans_monthly_analysis_limit
        check (monthly_analysis_limit > 0),
    constraint billing_plans_history_retention_days
        check (history_retention_days is null or history_retention_days > 0)
);

insert into public.billing_plans (
    plan_id,
    tier,
    monthly_analysis_limit,
    history_retention_days,
    is_active
)
values
    ('free', 'free', 3, 30, true),
    ('pro', 'pro', 100, null, true)
on conflict (plan_id) do update
set tier = excluded.tier,
    monthly_analysis_limit = excluded.monthly_analysis_limit,
    history_retention_days = excluded.history_retention_days,
    is_active = excluded.is_active;

create table if not exists public.analyses (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references public.tenants (id) on delete cascade,
    created_by uuid not null default auth.uid() references auth.users (id) on delete restrict,
    parent_analysis_id uuid,
    client_analysis_id text not null,
    idempotency_key text not null,
    analysis_mode text not null,
    input_status text not null,
    recommendation text not null,
    confidence text not null,
    recommended_opportunity_id text,
    official_score numeric(5, 2),
    executive_summary text not null,
    input_schema_version text not null,
    output_schema_version text not null,
    score_version text not null,
    input_payload jsonb not null,
    result_payload jsonb not null,
    processed_at timestamptz not null,
    created_at timestamptz not null default now(),
    constraint analyses_tenant_id_id_unique
        unique (tenant_id, id),
    constraint analyses_tenant_client_analysis_unique
        unique (tenant_id, client_analysis_id),
    constraint analyses_tenant_idempotency_unique
        unique (tenant_id, idempotency_key),
    constraint analyses_parent_same_tenant
        foreign key (tenant_id, parent_analysis_id)
        references public.analyses (tenant_id, id)
        on delete restrict,
    constraint analyses_client_analysis_id_length
        check (char_length(btrim(client_analysis_id)) between 1 and 128),
    constraint analyses_idempotency_key_length
        check (char_length(btrim(idempotency_key)) between 8 and 128),
    constraint analyses_analysis_mode
        check (analysis_mode in ('pre_test', 'campaign_diagnosis', 'reassessment')),
    constraint analyses_input_status
        check (input_status in ('sufficient', 'partial', 'insufficient', 'invalid')),
    constraint analyses_confidence
        check (confidence in ('high', 'moderate', 'low', 'inconclusive')),
    constraint analyses_official_score
        check (official_score is null or official_score between 0 and 100),
    constraint analyses_input_payload_object
        check (jsonb_typeof(input_payload) = 'object'),
    constraint analyses_result_payload_object
        check (jsonb_typeof(result_payload) = 'object')
);

create table if not exists public.analysis_advanced_details (
    analysis_id uuid primary key,
    tenant_id uuid not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    constraint analysis_advanced_details_analysis_tenant_fk
        foreign key (tenant_id, analysis_id)
        references public.analyses (tenant_id, id)
        on delete cascade,
    constraint analysis_advanced_details_payload_object
        check (jsonb_typeof(payload) = 'object')
);

create index if not exists analyses_tenant_created_at_idx
    on public.analyses (tenant_id, created_at desc, id desc);

create index if not exists analyses_tenant_recommendation_idx
    on public.analyses (tenant_id, recommendation, created_at desc);

create index if not exists analyses_tenant_input_status_idx
    on public.analyses (tenant_id, input_status, created_at desc);

create index if not exists analyses_created_by_idx
    on public.analyses (created_by, tenant_id, created_at desc);

create index if not exists analysis_advanced_details_tenant_idx
    on public.analysis_advanced_details (tenant_id, analysis_id);

drop trigger if exists billing_plans_set_updated_at on public.billing_plans;
create trigger billing_plans_set_updated_at
before update on public.billing_plans
for each row execute function private.set_updated_at();

comment on table public.billing_plans is
    'Server-authoritative SaaS plan catalog. Clients cannot mutate pricing or entitlements.';
comment on table public.analyses is
    'Immutable tenant-scoped validated analysis history and executive result payload.';
comment on table public.analysis_advanced_details is
    'PRO-only analysis payload isolated from the executive history projection.';

commit;
