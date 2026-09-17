-- Intake versionada: preserva o contexto usado para propor um backlog sem duplicar o cliente.
create table if not exists project_planning_intakes (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  schema_key text not null check (schema_key in ('retail_v1')),
  schema_version integer not null check (schema_version > 0),
  status text not null default 'draft' check (status in ('draft', 'finalized')),
  title text not null,
  objective text not null,
  answers jsonb not null default '{}'::jsonb,
  derived_context jsonb not null default '{}'::jsonb,
  created_by uuid references users(id) on delete set null,
  finalized_by uuid references users(id) on delete set null,
  finalized_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (jsonb_typeof(answers) = 'object'),
  check (jsonb_typeof(derived_context) = 'object')
);

create index if not exists project_planning_intakes_project_idx
  on project_planning_intakes (project_id, updated_at desc);

alter table project_plans
  add column if not exists planning_intake_id uuid references project_planning_intakes(id) on delete set null,
  add column if not exists intake_snapshot jsonb not null default '{}'::jsonb;

alter table project_plans
  drop constraint if exists project_plans_intake_snapshot_object_check;

alter table project_plans
  add constraint project_plans_intake_snapshot_object_check
    check (jsonb_typeof(intake_snapshot) = 'object');

create index if not exists project_plans_intake_idx on project_plans (planning_intake_id);
