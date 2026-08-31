-- WEB-NAV-002: preferências persistentes de navegação por usuário.

create table if not exists workspace_favorites (
  user_id uuid not null references users(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, workspace_id)
);

create table if not exists workspace_saved_views (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  tenant_organization_id uuid references organizations(id) on delete cascade,
  name text not null,
  filters jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, tenant_organization_id, name)
);

create index if not exists workspace_saved_views_user_idx
  on workspace_saved_views (user_id, updated_at desc);

create or replace function workspace_is_assigned(target_workspace_id uuid, target_user_id uuid)
returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from workspace_assignments wa
    where wa.workspace_id = target_workspace_id
      and (
        wa.user_id = target_user_id
        or exists (
          select 1
          from team_memberships tm
          where tm.team_id = wa.team_id and tm.user_id = target_user_id
        )
      )
  )
$$;
