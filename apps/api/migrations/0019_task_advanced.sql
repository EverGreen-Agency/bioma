-- 0019_task_advanced.sql

create table if not exists eg_task_subtasks (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references eg_tasks(id) on delete cascade,
  title text not null,
  is_completed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists eg_task_subtasks_task_idx on eg_task_subtasks(task_id);

alter table eg_tasks add column if not exists recurrence text default 'none';
