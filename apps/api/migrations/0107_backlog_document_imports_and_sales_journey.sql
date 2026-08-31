-- Backlog operacional, importacao documental e jornada comercial.
--
-- O Work Graph continua sendo a fonte canonica dos artefatos de planejamento;
-- tarefas continuam sendo a fonte canonica da execucao. A ligacao entre ambos
-- e explicita, auditavel e idempotente.

alter table work_items drop constraint if exists work_items_kind_check;
alter table work_items
  add constraint work_items_kind_check check (kind in (
    'goal', 'spec', 'story', 'decision', 'plan', 'milestone',
    'opportunity_event', 'deliverable', 'test', 'evidence', 'release', 'asset'
  ));

alter table work_items
  add column if not exists backlog_status text not null default 'candidate',
  add column if not exists priority text not null default 'medium',
  add column if not exists rank integer not null default 0,
  add column if not exists acceptance_criteria text,
  add column if not exists definition_of_done text,
  add column if not exists story_points integer,
  add column if not exists planned_start_at date,
  add column if not exists planned_end_at date,
  add column if not exists materialized_task_id uuid references eg_tasks(id) on delete set null;

alter table work_items drop constraint if exists work_items_backlog_status_check;
alter table work_items
  add constraint work_items_backlog_status_check check (
    backlog_status in ('candidate', 'backlog', 'ready', 'in_progress', 'done', 'rejected')
  );
alter table work_items drop constraint if exists work_items_priority_check;
alter table work_items
  add constraint work_items_priority_check check (priority in ('low', 'medium', 'high', 'critical'));
alter table work_items drop constraint if exists work_items_story_points_check;
alter table work_items
  add constraint work_items_story_points_check check (story_points is null or story_points between 1 and 100);
alter table work_items drop constraint if exists work_items_planned_dates_check;
alter table work_items
  add constraint work_items_planned_dates_check check (
    planned_start_at is null or planned_end_at is null or planned_end_at >= planned_start_at
  );

create index if not exists work_items_backlog_idx
  on work_items (workspace_id, project_id, backlog_status, priority, rank, updated_at desc);

create table if not exists project_document_imports (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  source_name text not null,
  content_type text not null,
  content_hash text not null,
  source_size_bytes integer not null check (source_size_bytes > 0),
  extracted_title text,
  extracted_text text not null,
  extraction_version text not null,
  status text not null default 'draft'
    check (status in ('draft', 'materialized', 'rejected')),
  candidates jsonb not null default '[]'::jsonb,
  warnings jsonb not null default '[]'::jsonb,
  materialized_item_ids jsonb not null default '[]'::jsonb,
  created_by uuid references users(id) on delete set null,
  materialized_by uuid references users(id) on delete set null,
  materialized_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (jsonb_typeof(candidates) = 'array'),
  check (jsonb_typeof(warnings) = 'array'),
  check (jsonb_typeof(materialized_item_ids) = 'array'),
  unique (project_id, content_hash)
);

create index if not exists project_document_imports_project_idx
  on project_document_imports (project_id, created_at desc);

alter table work_items
  add column if not exists source_document_import_id uuid
    references project_document_imports(id) on delete set null;

create table if not exists sales_journey_snapshots (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references sales_copilot_sessions(id) on delete cascade,
  workspace_id uuid references workspaces(id) on delete set null,
  opportunity_id uuid references opportunity_radar(id) on delete set null,
  current_funnel_stage text not null,
  funnel_map jsonb not null default '[]'::jsonb,
  journey_stages jsonb not null default '[]'::jsonb,
  scores jsonb not null default '{}'::jsonb,
  bottlenecks jsonb not null default '[]'::jsonb,
  recommended_actions jsonb not null default '[]'::jsonb,
  evidence_refs jsonb not null default '[]'::jsonb,
  generation_mode text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (jsonb_typeof(funnel_map) = 'array'),
  check (jsonb_typeof(journey_stages) = 'array'),
  check (jsonb_typeof(scores) = 'object'),
  check (jsonb_typeof(bottlenecks) = 'array'),
  check (jsonb_typeof(recommended_actions) = 'array'),
  check (jsonb_typeof(evidence_refs) = 'array')
);

create index if not exists sales_journey_snapshots_opportunity_idx
  on sales_journey_snapshots (opportunity_id, updated_at desc)
  where opportunity_id is not null;

comment on table project_document_imports is
  'Snapshot textual nao executavel de um documento importado, seus candidatos e a decisao HITL de materializacao.';
comment on table sales_journey_snapshots is
  'Projecao evidence-backed do funil e da jornada calculada a partir de uma sessao do Sales Copilot.';
