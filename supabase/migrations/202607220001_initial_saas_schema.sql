begin;

create schema if not exists private;

revoke all on schema private from public;
revoke all on schema private from anon;
revoke all on schema private from authenticated;

create table if not exists public.profiles (
    user_id uuid primary key references auth.users (id) on delete cascade,
    display_name text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint profiles_display_name_length
        check (char_length(btrim(display_name)) between 1 and 128)
);

create table if not exists public.tenants (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    owner_user_id uuid not null references auth.users (id) on delete restrict,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint tenants_name_length
        check (char_length(btrim(name)) between 1 and 128)
);

create table if not exists public.tenant_memberships (
    tenant_id uuid not null references public.tenants (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    role text not null default 'member',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (tenant_id, user_id),
    constraint tenant_memberships_role
        check (role in ('owner', 'admin', 'member'))
);

create table if not exists public.subscriptions (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null unique references public.tenants (id) on delete cascade,
    provider text not null,
    provider_customer_id text,
    provider_subscription_id text,
    plan_id text not null,
    status text not null,
    current_period_start timestamptz,
    current_period_end timestamptz,
    cancel_at_period_end boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint subscriptions_provider_length
        check (char_length(btrim(provider)) between 1 and 64),
    constraint subscriptions_plan_id_format
        check (plan_id ~ '^[a-z0-9][a-z0-9_-]{1,63}$'),
    constraint subscriptions_status
        check (status in (
            'trialing',
            'active',
            'past_due',
            'paused',
            'canceled',
            'incomplete',
            'incomplete_expired',
            'unpaid'
        )),
    constraint subscriptions_period_order
        check (
            current_period_start is null
            or current_period_end is null
            or current_period_end >= current_period_start
        )
);

create table if not exists public.projects (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references public.tenants (id) on delete cascade,
    created_by uuid not null default auth.uid() references auth.users (id) on delete restrict,
    name text not null,
    description text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint projects_name_length
        check (char_length(btrim(name)) between 1 and 128),
    constraint projects_description_length
        check (description is null or char_length(description) <= 4000)
);

create index if not exists tenant_memberships_user_id_idx
    on public.tenant_memberships (user_id, tenant_id);

create unique index if not exists subscriptions_provider_customer_id_uidx
    on public.subscriptions (provider, provider_customer_id)
    where provider_customer_id is not null;

create unique index if not exists subscriptions_provider_subscription_id_uidx
    on public.subscriptions (provider, provider_subscription_id)
    where provider_subscription_id is not null;

create index if not exists projects_tenant_id_idx
    on public.projects (tenant_id, id);

create index if not exists projects_created_by_idx
    on public.projects (created_by, tenant_id);

comment on table public.profiles is
    'User-owned profile data linked one-to-one with auth.users.';
comment on table public.tenants is
    'SaaS tenant boundary. Authorization is resolved through tenant_memberships.';
comment on table public.tenant_memberships is
    'Authoritative user-to-tenant membership and tenant-local role mapping.';
comment on table public.subscriptions is
    'Server-managed billing state. Authenticated clients have read-only access.';
comment on table public.projects is
    'Tenant-scoped projects protected by PostgreSQL row-level security.';

commit;
