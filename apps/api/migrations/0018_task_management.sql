-- 0018_task_management.sql

create table if not exists eg_task_lists (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  name text not null,
  type text not null check (type in ('social', 'growth', 'tech', 'general')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists eg_task_lists_workspace_idx on eg_task_lists(workspace_id);

create table if not exists eg_tasks (
  id uuid primary key default gen_random_uuid(),
  list_id uuid not null references eg_task_lists(id) on delete cascade,
  title text not null,
  description text,
  status text not null,
  group_status text not null check (group_status in ('NOT_STARTED', 'ACTIVE', 'DONE', 'CLOSED')),
  priority text check (priority in ('Alta', 'Média', 'Baixa')),
  assignee_id uuid references users(id) on delete set null,
  owner_id uuid references users(id) on delete set null,
  due_date timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists eg_tasks_list_idx on eg_tasks(list_id);

create table if not exists eg_task_custom_fields (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references eg_tasks(id) on delete cascade,
  field_name text not null,
  field_value text not null,
  unique (task_id, field_name)
);

create table if not exists eg_task_dependencies (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references eg_tasks(id) on delete cascade,
  depends_on_task_id uuid not null references eg_tasks(id) on delete cascade,
  type text not null default 'waiting_on',
  unique (task_id, depends_on_task_id)
);
