-- Inteligência de reunião do Copiloto: consentimento, participantes,
-- diarização, sugestões ao vivo e compromissos materializáveis com HITL.
alter table sales_copilot_sessions
  add column if not exists meeting_provider text not null default 'manual',
  add column if not exists meeting_url text,
  add column if not exists external_meeting_id text,
  add column if not exists consent_status text not null default 'pending',
  add column if not exists consent_recorded_at timestamptz,
  add column if not exists retention_until timestamptz,
  add column if not exists ingest_token_hash text,
  add column if not exists live_context jsonb not null default '{}'::jsonb;

alter table sales_copilot_sessions
  drop constraint if exists sales_copilot_sessions_meeting_provider_check,
  drop constraint if exists sales_copilot_sessions_consent_status_check,
  drop constraint if exists sales_copilot_sessions_live_context_check;

alter table sales_copilot_sessions
  add constraint sales_copilot_sessions_meeting_provider_check
    check (meeting_provider in ('manual', 'google_meet', 'microsoft_teams')),
  add constraint sales_copilot_sessions_consent_status_check
    check (consent_status in ('pending', 'granted', 'revoked')),
  add constraint sales_copilot_sessions_live_context_check
    check (jsonb_typeof(live_context) = 'object');

create table if not exists sales_copilot_participants (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sales_copilot_sessions(id) on delete cascade,
  display_name text not null,
  participant_group text not null default 'unknown'
    check (participant_group in ('eg_team', 'client', 'partner', 'unknown')),
  organization_name text,
  job_title text,
  seniority text not null default 'unknown'
    check (seniority in ('individual', 'manager', 'director', 'c_level', 'owner', 'unknown')),
  decision_role text not null default 'unknown'
    check (decision_role in ('champion', 'decision_maker', 'influencer', 'technical', 'user', 'unknown')),
  email text,
  external_speaker_id text,
  context_notes text,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (session_id, external_speaker_id)
);

create index if not exists sales_copilot_participants_session_idx
  on sales_copilot_participants (session_id, created_at);

create table if not exists sales_copilot_transcript_segments (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sales_copilot_sessions(id) on delete cascade,
  participant_id uuid references sales_copilot_participants(id) on delete set null,
  idempotency_key text not null,
  source text not null default 'manual'
    check (source in ('manual', 'upload', 'google_meet', 'microsoft_teams', 'provider_webhook')),
  external_speaker_id text,
  speaker_label text,
  start_ms integer not null default 0 check (start_ms >= 0),
  end_ms integer check (end_ms is null or end_ms >= start_ms),
  content text not null,
  confidence numeric(5,4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  is_final boolean not null default true,
  sequence integer not null,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (session_id, idempotency_key)
);

create index if not exists sales_copilot_segments_session_idx
  on sales_copilot_transcript_segments (session_id, sequence, created_at);

create table if not exists sales_copilot_live_suggestions (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sales_copilot_sessions(id) on delete cascade,
  suggestion_type text not null
    check (suggestion_type in ('question', 'objection_response', 'risk', 'opportunity', 'next_step')),
  title text not null,
  content text not null,
  rationale text,
  confidence numeric(5,4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  source_refs jsonb not null default '[]'::jsonb,
  generation_mode text not null default 'preview',
  status text not null default 'active'
    check (status in ('active', 'used', 'dismissed')),
  created_at timestamptz not null default now(),
  check (jsonb_typeof(source_refs) = 'array')
);

create index if not exists sales_copilot_suggestions_session_idx
  on sales_copilot_live_suggestions (session_id, created_at desc);

create table if not exists sales_copilot_actions (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sales_copilot_sessions(id) on delete cascade,
  action_type text not null
    check (action_type in ('follow_up_task', 'proposal_revision', 'project_update')),
  title text not null,
  detail text,
  owner_hint text,
  due_at timestamptz,
  source_refs jsonb not null default '[]'::jsonb,
  status text not null default 'proposed'
    check (status in ('proposed', 'approved', 'materialized', 'dismissed', 'failed')),
  idempotency_key text,
  materialized_ref jsonb not null default '{}'::jsonb,
  created_by uuid references users(id) on delete set null,
  approved_by uuid references users(id) on delete set null,
  materialized_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (jsonb_typeof(source_refs) = 'array'),
  check (jsonb_typeof(materialized_ref) = 'object'),
  unique (session_id, idempotency_key)
);

create index if not exists sales_copilot_actions_session_idx
  on sales_copilot_actions (session_id, status, created_at);
