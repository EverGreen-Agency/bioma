-- Ciclo comercial completo: revisão, envio rastreado, aceite, conversão HITL e copiloto.
alter table commercial_proposals
  add column if not exists content_markdown text not null default '',
  add column if not exists content_sections jsonb not null default '[]'::jsonb,
  add column if not exists claims jsonb not null default '[]'::jsonb,
  add column if not exists claims_review_status text not null default 'pending',
  add column if not exists archived_at timestamptz,
  add column if not exists viewed_at timestamptz,
  add column if not exists approved_at timestamptz,
  add column if not exists sent_at timestamptz,
  add column if not exists negotiating_at timestamptz,
  add column if not exists won_at timestamptz,
  add column if not exists lost_at timestamptz,
  add column if not exists acceptance_status text not null default 'not_requested',
  add column if not exists accepted_at timestamptz,
  add column if not exists accepted_by_name text,
  add column if not exists accepted_by_email text;

alter table commercial_proposals
  drop constraint if exists commercial_proposals_content_sections_check,
  drop constraint if exists commercial_proposals_claims_check,
  drop constraint if exists commercial_proposals_claims_review_status_check,
  drop constraint if exists commercial_proposals_acceptance_status_check;

alter table commercial_proposals
  add constraint commercial_proposals_content_sections_check
    check (jsonb_typeof(content_sections) = 'array'),
  add constraint commercial_proposals_claims_check
    check (jsonb_typeof(claims) = 'array'),
  add constraint commercial_proposals_claims_review_status_check
    check (claims_review_status in ('pending', 'approved', 'rejected')),
  add constraint commercial_proposals_acceptance_status_check
    check (acceptance_status in ('not_requested', 'pending', 'accepted', 'rejected'));

create table if not exists proposal_events (
  id uuid primary key default gen_random_uuid(),
  proposal_id uuid not null references commercial_proposals(id) on delete cascade,
  event_type text not null,
  actor_user_id uuid references users(id) on delete set null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (jsonb_typeof(payload) = 'object')
);

create index if not exists proposal_events_proposal_idx
  on proposal_events (proposal_id, created_at desc);

create table if not exists proposal_deliveries (
  id uuid primary key default gen_random_uuid(),
  proposal_id uuid not null references commercial_proposals(id) on delete cascade,
  channel text not null check (channel in ('share_link', 'manual_email', 'signature_adapter')),
  recipient_name text,
  recipient_email text,
  provider text,
  external_id text,
  status text not null default 'prepared'
    check (status in ('prepared', 'sent', 'delivered', 'accepted', 'rejected', 'failed')),
  metadata jsonb not null default '{}'::jsonb,
  sent_at timestamptz,
  delivered_at timestamptz,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (jsonb_typeof(metadata) = 'object')
);

create index if not exists proposal_deliveries_proposal_idx
  on proposal_deliveries (proposal_id, created_at desc);

create table if not exists proposal_conversions (
  id uuid primary key default gen_random_uuid(),
  proposal_id uuid not null unique references commercial_proposals(id) on delete cascade,
  idempotency_key text not null unique,
  project_id uuid not null references projects(id) on delete restrict,
  contract_id uuid not null references project_contracts(id) on delete restrict,
  plan_id uuid references project_plans(id) on delete set null,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

alter table project_planning_intakes
  drop constraint if exists project_planning_intakes_schema_key_check;

alter table project_planning_intakes
  add constraint project_planning_intakes_schema_key_check
    check (schema_key in ('retail_v1', 'tech_v1', 'growth_social_v1'));

create table if not exists sales_copilot_sessions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id) on delete set null,
  proposal_id uuid references commercial_proposals(id) on delete set null,
  title text not null,
  session_type text not null default 'sales_call'
    check (session_type in ('sales_call', 'discovery', 'proposal_review', 'follow_up')),
  language text not null default 'pt-BR',
  status text not null default 'draft'
    check (status in ('draft', 'prepared', 'active', 'completed', 'cancelled')),
  realtime_status text not null default 'not_configured'
    check (realtime_status in ('not_configured', 'adapter_ready', 'live', 'failed')),
  objective text,
  participant_context text,
  knowledge_snapshot jsonb not null default '{}'::jsonb,
  preparation_brief jsonb not null default '{}'::jsonb,
  transcript text not null default '',
  summary text,
  duration_seconds integer not null default 0 check (duration_seconds >= 0),
  created_by uuid references users(id) on delete set null,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (jsonb_typeof(knowledge_snapshot) = 'object'),
  check (jsonb_typeof(preparation_brief) = 'object')
);

create index if not exists sales_copilot_sessions_created_idx
  on sales_copilot_sessions (created_at desc);
create index if not exists sales_copilot_sessions_workspace_idx
  on sales_copilot_sessions (workspace_id, created_at desc);

create table if not exists sales_copilot_events (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sales_copilot_sessions(id) on delete cascade,
  event_type text not null
    check (event_type in ('transcript_chunk', 'objection', 'insight', 'note', 'action_item')),
  content text not null,
  recommendation text,
  source_refs jsonb not null default '[]'::jsonb,
  sequence integer not null default 0,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  check (jsonb_typeof(source_refs) = 'array')
);

create index if not exists sales_copilot_events_session_idx
  on sales_copilot_events (session_id, sequence, created_at);
