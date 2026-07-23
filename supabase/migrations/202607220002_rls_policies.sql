begin;

create or replace function private.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create or replace function private.is_tenant_member(
    target_tenant_id uuid
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select auth.uid() is not null
        and exists (
            select 1
            from public.tenant_memberships as membership
            where membership.tenant_id = target_tenant_id
              and membership.user_id = auth.uid()
        );
$$;

create or replace function private.has_tenant_role(
    target_tenant_id uuid,
    allowed_roles text[]
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select auth.uid() is not null
        and exists (
            select 1
            from public.tenant_memberships as membership
            where membership.tenant_id = target_tenant_id
              and membership.user_id = auth.uid()
              and membership.role = any (allowed_roles)
        );
$$;

create or replace function private.bootstrap_tenant_owner()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.tenant_memberships (tenant_id, user_id, role)
    values (new.id, new.owner_user_id, 'owner')
    on conflict (tenant_id, user_id)
    do update set role = 'owner';
    return new;
end;
$$;

create or replace function private.protect_tenant_owner()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if new.owner_user_id is distinct from old.owner_user_id then
        raise exception 'tenant owner cannot be changed directly'
            using errcode = '42501';
    end if;
    return new;
end;
$$;

create or replace function private.protect_owner_membership()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    owner_id uuid;
begin
    select tenant.owner_user_id
      into owner_id
      from public.tenants as tenant
     where tenant.id = old.tenant_id;

    if tg_op = 'DELETE' then
        if old.user_id = owner_id then
            raise exception 'tenant owner membership cannot be removed or downgraded'
                using errcode = '42501';
        end if;
        return old;
    end if;

    if old.user_id = owner_id
       and (new.role <> 'owner' or new.user_id <> old.user_id
            or new.tenant_id <> old.tenant_id) then
        raise exception 'tenant owner membership cannot be removed or downgraded'
            using errcode = '42501';
    end if;
    return new;
end;
$$;

revoke all on function private.set_updated_at() from public;
revoke all on function private.is_tenant_member(uuid) from public;
revoke all on function private.has_tenant_role(uuid, text[]) from public;
revoke all on function private.bootstrap_tenant_owner() from public;
revoke all on function private.protect_tenant_owner() from public;
revoke all on function private.protect_owner_membership() from public;

grant usage on schema private to authenticated;
grant execute on function private.is_tenant_member(uuid) to authenticated;
grant execute on function private.has_tenant_role(uuid, text[]) to authenticated;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function private.set_updated_at();

drop trigger if exists tenants_set_updated_at on public.tenants;
create trigger tenants_set_updated_at
before update on public.tenants
for each row execute function private.set_updated_at();

drop trigger if exists tenant_memberships_set_updated_at on public.tenant_memberships;
create trigger tenant_memberships_set_updated_at
before update on public.tenant_memberships
for each row execute function private.set_updated_at();

drop trigger if exists subscriptions_set_updated_at on public.subscriptions;
create trigger subscriptions_set_updated_at
before update on public.subscriptions
for each row execute function private.set_updated_at();

drop trigger if exists projects_set_updated_at on public.projects;
create trigger projects_set_updated_at
before update on public.projects
for each row execute function private.set_updated_at();

drop trigger if exists tenants_bootstrap_owner on public.tenants;
create trigger tenants_bootstrap_owner
after insert on public.tenants
for each row execute function private.bootstrap_tenant_owner();

drop trigger if exists tenants_protect_owner on public.tenants;
create trigger tenants_protect_owner
before update of owner_user_id on public.tenants
for each row execute function private.protect_tenant_owner();

drop trigger if exists tenant_memberships_protect_owner on public.tenant_memberships;
create trigger tenant_memberships_protect_owner
before update or delete on public.tenant_memberships
for each row execute function private.protect_owner_membership();

alter table public.profiles enable row level security;
alter table public.profiles force row level security;
alter table public.tenants enable row level security;
alter table public.tenants force row level security;
alter table public.tenant_memberships enable row level security;
alter table public.tenant_memberships force row level security;
alter table public.subscriptions enable row level security;
alter table public.subscriptions force row level security;
alter table public.projects enable row level security;
alter table public.projects force row level security;

revoke all on table public.profiles from anon, authenticated;
revoke all on table public.tenants from anon, authenticated;
revoke all on table public.tenant_memberships from anon, authenticated;
revoke all on table public.subscriptions from anon, authenticated;
revoke all on table public.projects from anon, authenticated;

grant select, delete on table public.profiles to authenticated;
grant insert (user_id, display_name) on table public.profiles to authenticated;
grant update (display_name) on table public.profiles to authenticated;

grant select, delete on table public.tenants to authenticated;
grant insert (name, owner_user_id) on table public.tenants to authenticated;
grant update (name) on table public.tenants to authenticated;

grant select, delete on table public.tenant_memberships to authenticated;
grant insert (tenant_id, user_id, role) on table public.tenant_memberships to authenticated;
grant update (role) on table public.tenant_memberships to authenticated;

grant select (
    id,
    tenant_id,
    plan_id,
    status,
    current_period_start,
    current_period_end,
    cancel_at_period_end,
    created_at,
    updated_at
) on table public.subscriptions to authenticated;

grant select, delete on table public.projects to authenticated;
grant insert (tenant_id, name, description) on table public.projects to authenticated;
grant update (name, description) on table public.projects to authenticated;

drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own
on public.profiles for select
to authenticated
using (user_id = auth.uid());

drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own
on public.profiles for insert
to authenticated
with check (user_id = auth.uid());

drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own
on public.profiles for update
to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists profiles_delete_own on public.profiles;
create policy profiles_delete_own
on public.profiles for delete
to authenticated
using (user_id = auth.uid());

drop policy if exists tenants_select_member on public.tenants;
create policy tenants_select_member
on public.tenants for select
to authenticated
using (
    owner_user_id = auth.uid()
    or private.is_tenant_member(id)
);

drop policy if exists tenants_insert_owned on public.tenants;
create policy tenants_insert_owned
on public.tenants for insert
to authenticated
with check (owner_user_id = auth.uid());

drop policy if exists tenants_update_owner on public.tenants;
create policy tenants_update_owner
on public.tenants for update
to authenticated
using (owner_user_id = auth.uid())
with check (owner_user_id = auth.uid());

drop policy if exists tenants_delete_owner on public.tenants;
create policy tenants_delete_owner
on public.tenants for delete
to authenticated
using (owner_user_id = auth.uid());

drop policy if exists tenant_memberships_select_member on public.tenant_memberships;
create policy tenant_memberships_select_member
on public.tenant_memberships for select
to authenticated
using (private.is_tenant_member(tenant_id));

drop policy if exists tenant_memberships_insert_manager on public.tenant_memberships;
create policy tenant_memberships_insert_manager
on public.tenant_memberships for insert
to authenticated
with check (
    (
        role in ('admin', 'member')
        and private.has_tenant_role(tenant_id, array['owner'])
    )
    or (
        role = 'member'
        and private.has_tenant_role(tenant_id, array['admin'])
    )
);

drop policy if exists tenant_memberships_update_manager on public.tenant_memberships;
create policy tenant_memberships_update_manager
on public.tenant_memberships for update
to authenticated
using (
    private.has_tenant_role(tenant_id, array['owner'])
    or (
        role = 'member'
        and private.has_tenant_role(tenant_id, array['admin'])
    )
)
with check (
    (
        role in ('admin', 'member')
        and private.has_tenant_role(tenant_id, array['owner'])
    )
    or (
        role = 'member'
        and private.has_tenant_role(tenant_id, array['admin'])
    )
);

drop policy if exists tenant_memberships_delete_manager on public.tenant_memberships;
create policy tenant_memberships_delete_manager
on public.tenant_memberships for delete
to authenticated
using (
    private.has_tenant_role(tenant_id, array['owner'])
    or (
        role = 'member'
        and private.has_tenant_role(tenant_id, array['admin'])
    )
);

drop policy if exists subscriptions_select_member on public.subscriptions;
create policy subscriptions_select_member
on public.subscriptions for select
to authenticated
using (private.is_tenant_member(tenant_id));

drop policy if exists projects_select_member on public.projects;
create policy projects_select_member
on public.projects for select
to authenticated
using (private.is_tenant_member(tenant_id));

drop policy if exists projects_insert_member on public.projects;
create policy projects_insert_member
on public.projects for insert
to authenticated
with check (
    created_by = auth.uid()
    and private.is_tenant_member(tenant_id)
);

drop policy if exists projects_update_authorized on public.projects;
create policy projects_update_authorized
on public.projects for update
to authenticated
using (
    created_by = auth.uid()
    or private.has_tenant_role(tenant_id, array['owner', 'admin'])
)
with check (
    private.is_tenant_member(tenant_id)
    and (
        created_by = auth.uid()
        or private.has_tenant_role(tenant_id, array['owner', 'admin'])
    )
);

drop policy if exists projects_delete_authorized on public.projects;
create policy projects_delete_authorized
on public.projects for delete
to authenticated
using (
    created_by = auth.uid()
    or private.has_tenant_role(tenant_id, array['owner', 'admin'])
);

comment on policy subscriptions_select_member on public.subscriptions is
    'Authenticated members may read billing state; client writes are deliberately denied.';

commit;
