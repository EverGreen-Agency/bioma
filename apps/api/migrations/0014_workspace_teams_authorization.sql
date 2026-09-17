-- TEAM-001 + AUTHZ-WS-001: carteira por time/usuário e papéis por workspace.

create table if not exists tenant_memberships (
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('tenant_admin', 'operator', 'approver', 'viewer')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (tenant_organization_id, user_id)
);

create table if not exists teams (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  name text not null,
  slug text not null,
  status text not null default 'active' check (status in ('active', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_organization_id, slug)
);

create table if not exists team_memberships (
  team_id uuid not null references teams(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null default 'member' check (role in ('manager', 'member')),
  created_at timestamptz not null default now(),
  primary key (team_id, user_id)
);

create table if not exists workspace_assignments (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  user_id uuid references users(id) on delete cascade,
  team_id uuid references teams(id) on delete cascade,
  role text not null check (role in ('workspace_manager', 'operator', 'approver', 'viewer')),
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint workspace_assignments_one_assignee_check check (
    (user_id is not null and team_id is null)
    or (user_id is null and team_id is not null)
  )
);

create unique index if not exists workspace_assignments_user_idx
  on workspace_assignments (workspace_id, user_id)
  where user_id is not null;

create unique index if not exists workspace_assignments_team_idx
  on workspace_assignments (workspace_id, team_id)
  where team_id is not null;

create index if not exists team_memberships_user_idx on team_memberships (user_id, team_id);
create index if not exists workspace_assignments_user_lookup_idx on workspace_assignments (user_id, workspace_id);
create index if not exists workspace_assignments_team_lookup_idx on workspace_assignments (team_id, workspace_id);

create or replace function workspace_access_role(target_workspace_id uuid, target_user_id uuid)
returns text
language sql
stable
as $$
  with target as (
    select id, tenant_organization_id, subject_organization_id, kind
    from workspaces
    where id = target_workspace_id and status = 'active'
  ), candidates as (
    select tm.role, 10 as priority
    from target t
    join tenant_memberships tm
      on tm.tenant_organization_id = t.tenant_organization_id
     and tm.user_id = target_user_id
     and tm.role = 'tenant_admin'

    union all

    select wa.role,
      case wa.role
        when 'workspace_manager' then 20
        when 'operator' then 30
        when 'approver' then 40
        else 50
      end
    from target t
    join workspace_assignments wa
      on wa.workspace_id = t.id
     and wa.user_id = target_user_id

    union all

    select wa.role,
      case wa.role
        when 'workspace_manager' then 20
        when 'operator' then 30
        when 'approver' then 40
        else 50
      end
    from target t
    join workspace_assignments wa on wa.workspace_id = t.id
    join team_memberships team_member
      on team_member.team_id = wa.team_id
     and team_member.user_id = target_user_id

    union all

    select 'client_user', 60
    from target t
    join memberships membership
      on membership.organization_id = t.subject_organization_id
     and membership.user_id = target_user_id
     and membership.role = 'client_user'
    where t.kind = 'client'
  )
  select role
  from candidates
  order by priority
  limit 1
$$;

create or replace function enforce_workspace_assignment_tenant()
returns trigger
language plpgsql
as $$
declare
  workspace_tenant uuid;
  team_tenant uuid;
begin
  if new.team_id is null then
    return new;
  end if;

  select tenant_organization_id into workspace_tenant from workspaces where id = new.workspace_id;
  select tenant_organization_id into team_tenant from teams where id = new.team_id;
  if workspace_tenant is distinct from team_tenant then
    raise exception 'Time e workspace precisam pertencer ao mesmo tenant.';
  end if;
  return new;
end
$$;

drop trigger if exists workspace_assignment_tenant_guard on workspace_assignments;
create trigger workspace_assignment_tenant_guard
before insert or update on workspace_assignments
for each row execute function enforce_workspace_assignment_tenant();
