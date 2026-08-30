-- Fundação aditiva da Experiência V2.
--
-- Mantém as fontes de verdade atuais e adiciona continuidade entre conversa,
-- oportunidade, reunião, proposta, tarefa, documento e evidência. Work Graph é
-- rastreabilidade; nunca concede acesso e não exige banco de grafos.

-- 1. Oportunidade deixa de ser somente item importado do radar e pode receber
-- contexto operacional. Registros históricos permanecem válidos sem workspace.
alter table opportunity_radar
  add column if not exists workspace_id uuid references workspaces(id) on delete set null,
  add column if not exists owner_user_id uuid references users(id) on delete set null,
  add column if not exists next_action_at timestamptz,
  add column if not exists closed_at timestamptz;

create index if not exists opportunity_radar_workspace_idx
  on opportunity_radar (workspace_id, updated_at desc);
create index if not exists opportunity_radar_owner_idx
  on opportunity_radar (owner_user_id, status, updated_at desc);
create index if not exists opportunity_radar_next_action_idx
  on opportunity_radar (next_action_at) where next_action_at is not null;

create table if not exists opportunity_contacts (
  opportunity_id uuid not null references opportunity_radar(id) on delete cascade,
  lead_id uuid not null references leads(id) on delete cascade,
  relationship_role text not null default 'contact'
    check (relationship_role in ('contact', 'champion', 'decision_maker', 'influencer', 'billing')),
  is_primary boolean not null default false,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  primary key (opportunity_id, lead_id)
);

create unique index if not exists opportunity_contacts_one_primary_idx
  on opportunity_contacts (opportunity_id) where is_primary;

create table if not exists commercial_activities (
  id uuid primary key default gen_random_uuid(),
  opportunity_id uuid not null references opportunity_radar(id) on delete cascade,
  activity_type text not null
    check (activity_type in (
      'captured', 'status_changed', 'note', 'follow_up_prepared', 'follow_up_sent',
      'message_received', 'meeting_scheduled', 'meeting_completed', 'proposal_created',
      'proposal_sent', 'decision', 'won', 'lost'
    )),
  direction text not null default 'internal'
    check (direction in ('internal', 'inbound', 'outbound')),
  channel text,
  title text not null,
  body text,
  occurred_at timestamptz not null default now(),
  source_kind text not null default 'manual',
  source_ref text,
  idempotency_key text,
  metadata jsonb not null default '{}'::jsonb,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  check (jsonb_typeof(metadata) = 'object'),
  unique (opportunity_id, idempotency_key)
);

create index if not exists commercial_activities_timeline_idx
  on commercial_activities (opportunity_id, occurred_at desc, created_at desc);

-- A porta de entrada do cliente é uma solicitação orientada a resultado, não
-- acesso ao backlog interno da EG. A triagem pode materializar tarefas depois.
create table if not exists client_requests (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  category text not null default 'request'
    check (category in ('request', 'question', 'change', 'input')),
  title text not null,
  detail text,
  status text not null default 'submitted'
    check (status in ('submitted', 'triaged', 'in_progress', 'waiting_client', 'done', 'declined')),
  priority text not null default 'normal'
    check (priority in ('low', 'normal', 'high', 'urgent')),
  requested_by uuid references users(id) on delete set null,
  assigned_to uuid references users(id) on delete set null,
  resolution_summary text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists client_requests_workspace_idx
  on client_requests (workspace_id, status, updated_at desc);

-- 2. Reunião e conversa compartilham o mesmo contexto comercial.
alter table sales_copilot_sessions
  add column if not exists opportunity_id uuid references opportunity_radar(id) on delete set null;

create index if not exists sales_copilot_sessions_opportunity_idx
  on sales_copilot_sessions (opportunity_id, created_at desc);

create table if not exists copilot_thread_entities (
  thread_id uuid not null references copilot_threads(id) on delete cascade,
  entity_type text not null
    check (entity_type in ('workspace', 'project', 'opportunity', 'proposal', 'task', 'document', 'artifact')),
  entity_id uuid not null,
  relationship text not null default 'context'
    check (relationship in ('context', 'created', 'updated', 'referenced')),
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  primary key (thread_id, entity_type, entity_id, relationship)
);

create index if not exists copilot_thread_entities_target_idx
  on copilot_thread_entities (entity_type, entity_id, created_at desc);

-- Blocos são dados tipados validados pelo backend, nunca HTML/JS do modelo.
alter table copilot_runs
  add column if not exists response_blocks jsonb not null default '[]'::jsonb;

alter table copilot_runs
  drop constraint if exists copilot_runs_response_blocks_check;
alter table copilot_runs
  add constraint copilot_runs_response_blocks_check
    check (jsonb_typeof(response_blocks) = 'array');

-- 3. Tarefa separa contexto, aceite e Definition of Done sem destruir dados.
alter table eg_tasks
  add column if not exists acceptance_criteria text,
  add column if not exists definition_of_done text,
  add column if not exists semantic_review_required boolean not null default false;

update eg_tasks
set definition_of_done = description,
    semantic_review_required = description is not null and btrim(description) <> ''
where definition_of_done is null;

comment on column eg_tasks.description is
  'Contexto, problema e resultado esperado. Nao usar como Definition of Done em novas escritas.';
comment on column eg_tasks.acceptance_criteria is
  'Comportamento verificavel que satisfaz a necessidade de negocio.';
comment on column eg_tasks.definition_of_done is
  'Gates tecnicos e operacionais necessarios para encerrar a tarefa.';

-- 4. Rastreabilidade entre fontes de verdade. A aplicação valida existência,
-- tenancy e capability de origem e destino antes de inserir ou revelar links.
create table if not exists work_items (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  project_id uuid references projects(id) on delete cascade,
  kind text not null
    check (kind in ('goal', 'spec', 'story', 'decision', 'plan', 'deliverable', 'test', 'evidence', 'release', 'asset')),
  title text not null,
  summary text,
  status text not null default 'draft'
    check (status in ('draft', 'active', 'done', 'superseded', 'archived')),
  external_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (jsonb_typeof(metadata) = 'object')
);

create index if not exists work_items_workspace_idx
  on work_items (workspace_id, project_id, kind, updated_at desc);

create table if not exists work_entity_links (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  source_type text not null,
  source_id uuid not null,
  relation_type text not null
    check (relation_type in (
      'derives_from', 'decomposes_into', 'implements', 'tests', 'evidences',
      'decides', 'blocks', 'supersedes', 'reuses', 'materializes'
    )),
  target_type text not null,
  target_id uuid not null,
  metadata jsonb not null default '{}'::jsonb,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  check (source_type <> '' and target_type <> ''),
  check (source_type <> target_type or source_id <> target_id),
  check (jsonb_typeof(metadata) = 'object'),
  unique (workspace_id, source_type, source_id, relation_type, target_type, target_id)
);

create index if not exists work_entity_links_source_idx
  on work_entity_links (workspace_id, source_type, source_id, created_at desc);
create index if not exists work_entity_links_target_idx
  on work_entity_links (workspace_id, target_type, target_id, created_at desc);
