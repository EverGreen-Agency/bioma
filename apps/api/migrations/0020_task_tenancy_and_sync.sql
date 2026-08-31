-- TASK-SEC-001: tenancy, external identity and idempotent recurrence.

alter table eg_task_lists
  add column if not exists external_source text,
  add column if not exists external_id text;

create unique index if not exists eg_task_lists_external_identity_idx
  on eg_task_lists (workspace_id, external_source, external_id)
  where external_source is not null and external_id is not null;

alter table eg_tasks
  add column if not exists external_source text,
  add column if not exists external_id text,
  add column if not exists recurrence_source_task_id uuid references eg_tasks(id) on delete set null;

create unique index if not exists eg_tasks_external_identity_idx
  on eg_tasks (list_id, external_source, external_id)
  where external_source is not null and external_id is not null;

create unique index if not exists eg_tasks_recurrence_source_idx
  on eg_tasks (recurrence_source_task_id)
  where recurrence_source_task_id is not null;

alter table eg_task_subtasks
  add column if not exists external_source text,
  add column if not exists external_id text;

create unique index if not exists eg_task_subtasks_external_identity_idx
  on eg_task_subtasks (task_id, external_source, external_id)
  where external_source is not null and external_id is not null;

alter table eg_task_dependencies
  drop constraint if exists eg_task_dependencies_no_self_check;

alter table eg_task_dependencies
  add constraint eg_task_dependencies_no_self_check
  check (task_id <> depends_on_task_id);
