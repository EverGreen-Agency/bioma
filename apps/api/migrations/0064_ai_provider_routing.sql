-- Migration 0064: plano de controle e execução multi-provider de IA.
--
-- Separa fornecedor, canal de acesso, conta e modelo. Uma assinatura pessoal
-- (Codex, Claude Code, Antigravity CLI) não é equivalente a uma conta de API.
-- Segredos não são persistidos aqui: auth_ref aponta apenas para configuração
-- externa/ambiente ou keyring do runner.

create table if not exists ai_provider_accounts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  subscription_id uuid references ai_provider_subscriptions(id) on delete set null,
  provider text not null check (provider in ('openai', 'anthropic', 'google')),
  channel text not null,
  display_name text not null,
  auth_mode text not null check (
    auth_mode in ('chatgpt', 'claude_subscription', 'google_subscription', 'api_key', 'vertex_adc', 'service_account')
  ),
  execution_mode text not null check (
    execution_mode in ('app_server', 'local_cli', 'sdk', 'api', 'manual_handoff')
  ),
  auth_ref text,
  status text not null default 'active' check (status in ('active', 'degraded', 'unavailable', 'paused')),
  is_default boolean not null default false,
  capabilities text[] not null default '{}'::text[],
  settings jsonb not null default '{}'::jsonb,
  health_detail text,
  last_probe_at timestamptz,
  created_by uuid references users(id) on delete set null,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, channel, display_name)
);

create unique index if not exists ai_provider_accounts_one_default_idx
  on ai_provider_accounts (organization_id, channel)
  where is_default and status <> 'paused';

create index if not exists ai_provider_accounts_route_idx
  on ai_provider_accounts (organization_id, status, provider, channel);

create table if not exists ai_model_catalog (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references ai_provider_accounts(id) on delete cascade,
  model_id text not null,
  display_name text not null,
  family text,
  capability_tier text not null default 'balanced'
    check (capability_tier in ('economy', 'balanced', 'frontier', 'specialist')),
  capabilities text[] not null default '{}'::text[],
  quality_score smallint not null default 50 check (quality_score between 0 and 100),
  cost_score smallint not null default 50 check (cost_score between 0 and 100),
  latency_score smallint not null default 50 check (latency_score between 0 and 100),
  context_window integer check (context_window is null or context_window > 0),
  enabled boolean not null default true,
  priority integer not null default 100,
  metadata jsonb not null default '{}'::jsonb,
  discovered_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (account_id, model_id)
);

create index if not exists ai_model_catalog_route_idx
  on ai_model_catalog (account_id, enabled, capability_tier, priority);

create table if not exists ai_quota_buckets (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references ai_provider_accounts(id) on delete cascade,
  bucket_key text not null,
  scope text not null default 'account' check (scope in ('account', 'workspace', 'model', 'model_family', 'credits')),
  model_id text,
  total_units numeric(20, 4),
  used_units numeric(20, 4),
  used_percent numeric(7, 4) check (used_percent is null or used_percent between 0 and 100),
  remaining_percent numeric(7, 4) check (remaining_percent is null or remaining_percent between 0 and 100),
  unit text not null default 'percent',
  window_duration_minutes integer check (window_duration_minutes is null or window_duration_minutes > 0),
  resets_at timestamptz,
  source text not null check (
    source in ('provider_api', 'provider_cli', 'provider_ui', 'bioma_metered', 'configured', 'unavailable')
  ),
  confidence text not null check (confidence in ('authoritative', 'measured', 'manual', 'unavailable')),
  measured_at timestamptz not null default now(),
  raw_metadata jsonb not null default '{}'::jsonb,
  notes text,
  created_by uuid references users(id) on delete set null,
  constraint ai_quota_bucket_values_check check (
    (total_units is null or total_units >= 0)
    and (used_units is null or used_units >= 0)
  )
);

create index if not exists ai_quota_buckets_latest_idx
  on ai_quota_buckets (account_id, bucket_key, model_id, measured_at desc);

create table if not exists ai_quota_collection_jobs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  account_id uuid not null references ai_provider_accounts(id) on delete cascade,
  requested_by uuid references users(id) on delete set null,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'completed', 'failed')),
  collector text not null,
  result jsonb,
  error_message text,
  attempts integer not null default 0,
  heartbeat_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ai_quota_collection_jobs_queue_idx
  on ai_quota_collection_jobs (status, created_at);

create table if not exists ai_routing_policies (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  task_kind text not null,
  capability text not null,
  name text not null,
  allowed_channels text[] not null default '{}'::text[],
  allowed_models text[] not null default '{}'::text[],
  preferred_tiers text[] not null default '{}'::text[],
  quality_weight smallint not null default 35 check (quality_weight between 0 and 100),
  quota_weight smallint not null default 25 check (quota_weight between 0 and 100),
  cost_weight smallint not null default 20 check (cost_weight between 0 and 100),
  reliability_weight smallint not null default 10 check (reliability_weight between 0 and 100),
  latency_weight smallint not null default 10 check (latency_weight between 0 and 100),
  minimum_quota_headroom numeric(7, 4) not null default 10
    check (minimum_quota_headroom between 0 and 100),
  requires_human_approval boolean not null default true,
  allow_fallback boolean not null default true,
  status text not null default 'active' check (status in ('draft', 'active', 'retired')),
  created_by uuid references users(id) on delete set null,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, task_kind)
);

create index if not exists ai_routing_policies_org_idx
  on ai_routing_policies (organization_id, status, task_kind);

create table if not exists ai_execution_attempts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  workflow_run_id uuid references ai_workflow_runs(id) on delete cascade,
  step_run_id uuid references ai_workflow_step_runs(id) on delete cascade,
  account_id uuid references ai_provider_accounts(id) on delete set null,
  model_catalog_id uuid references ai_model_catalog(id) on delete set null,
  attempt_number integer not null default 1 check (attempt_number > 0),
  status text not null default 'queued'
    check (status in ('queued', 'running', 'completed', 'failed', 'cancelled', 'skipped')),
  selection_score numeric(10, 4),
  selection_reason jsonb not null default '{}'::jsonb,
  quota_before jsonb not null default '[]'::jsonb,
  quota_after jsonb not null default '[]'::jsonb,
  input jsonb not null default '{}'::jsonb,
  output jsonb,
  input_units bigint check (input_units is null or input_units >= 0),
  output_units bigint check (output_units is null or output_units >= 0),
  cached_units bigint check (cached_units is null or cached_units >= 0),
  cost_cents bigint check (cost_cents is null or cost_cents >= 0),
  currency varchar(3) not null default 'USD',
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  external_event_id text,
  error_code text,
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  unique (step_run_id, attempt_number)
);

create index if not exists ai_execution_attempts_run_idx
  on ai_execution_attempts (workflow_run_id, step_run_id, attempt_number);

alter table ai_workflow_step_runs
  add column if not exists description text,
  add column if not exists task_kind text,
  add column if not exists capability text,
  add column if not exists routing_policy_id uuid references ai_routing_policies(id) on delete set null,
  add column if not exists account_id uuid references ai_provider_accounts(id) on delete set null,
  add column if not exists model_catalog_id uuid references ai_model_catalog(id) on delete set null,
  add column if not exists selection_reason jsonb not null default '{}'::jsonb,
  add column if not exists heartbeat_at timestamptz,
  add column if not exists attempts integer not null default 0;

create index if not exists ai_workflow_step_runs_queue_idx
  on ai_workflow_step_runs (status, created_at)
  where status = 'pending';
