create extension if not exists pgcrypto;

create table if not exists organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  type text not null check (type in ('eg', 'client')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  display_name text not null,
  password_hash text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists users_email_lower_idx on users (lower(email));

create table if not exists memberships (
  user_id uuid not null references users(id) on delete cascade,
  organization_id uuid not null references organizations(id) on delete cascade,
  role text not null check (role in ('eg_admin', 'client_user')),
  created_at timestamptz not null default now(),
  primary key (user_id, organization_id)
);

create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

create table if not exists clients (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null unique references organizations(id) on delete cascade,
  name text not null,
  status text not null default 'onboarding' check (status in ('onboarding', 'active', 'paused', 'archived')),
  responsible_name text,
  clickup_folder_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists artifacts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  title text not null,
  kind text not null,
  visibility text not null default 'internal' check (visibility in ('internal', 'client')),
  url text,
  content text,
  created_by uuid references users(id),
  created_at timestamptz not null default now()
);

create table if not exists deliverables (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  title text not null,
  status text not null default 'planned' check (status in ('planned', 'in_progress', 'waiting_approval', 'done', 'blocked')),
  due_at timestamptz,
  clickup_task_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists approvals (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  deliverable_id uuid references deliverables(id) on delete set null,
  requested_by uuid references users(id),
  decided_by uuid references users(id),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected', 'cancelled')),
  comment text,
  decided_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists clickup_mappings (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  clickup_workspace_id text,
  clickup_folder_id text,
  clickup_list_id text,
  created_at timestamptz not null default now(),
  unique (organization_id, clickup_workspace_id, clickup_folder_id, clickup_list_id)
);

create table if not exists sync_runs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  organization_id uuid references organizations(id) on delete cascade,
  status text not null check (status in ('ok', 'error', 'partial')),
  summary jsonb not null default '{}'::jsonb,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists ai_runs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  user_id uuid references users(id) on delete set null,
  provider text not null,
  model text not null,
  prompt_version text,
  input_schema text,
  output_schema text,
  estimated_cost numeric(12, 6),
  created_at timestamptz not null default now()
);

create table if not exists audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references users(id) on delete set null,
  organization_id uuid references organizations(id) on delete set null,
  event_type text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
