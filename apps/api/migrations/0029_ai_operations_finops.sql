-- AI-OPS-001: control plane de workflows e FinOps de IA da operação EG.
-- A migration cria apenas estrutura. Não popula assinaturas, cotas ou execuções.

create table if not exists ai_provider_subscriptions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  provider text not null,
  product_name text not null,
  billing_mode text not null check (billing_mode in ('subscription', 'api', 'hybrid')),
  billing_cycle text not null default 'monthly' check (billing_cycle in ('monthly', 'annual', 'custom')),
  billing_cycle_months integer not null default 1 check (billing_cycle_months between 1 and 120),
  amount_cents bigint not null default 0 check (amount_cents >= 0),
  currency varchar(3) not null default 'BRL',
  seats integer not null default 1 check (seats > 0),
  status text not null default 'active' check (status in ('active', 'paused', 'cancelled')),
  renews_at date,
  owner_label text,
  notes text,
  created_by uuid references users(id) on delete set null,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, provider, product_name)
);

create index if not exists ai_provider_subscriptions_org_status_idx
  on ai_provider_subscriptions (organization_id, status, provider);

create table if not exists ai_quota_snapshots (
  id uuid primary key default gen_random_uuid(),
  subscription_id uuid not null references ai_provider_subscriptions(id) on delete cascade,
  total_units numeric(20, 4),
  used_units numeric(20, 4),
  unit text not null,
  source text not null check (source in ('api', 'manual', 'configured', 'unavailable')),
  period_start date,
  period_end date,
  measured_at timestamptz not null default now(),
  notes text,
  created_by uuid references users(id) on delete set null,
  constraint ai_quota_snapshot_values_check check (
    (total_units is null or total_units >= 0)
    and (used_units is null or used_units >= 0)
  )
);

create index if not exists ai_quota_snapshots_latest_idx
  on ai_quota_snapshots (subscription_id, measured_at desc);

create table if not exists ai_workflow_definitions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  slug text not null,
  name text not null,
  version integer not null check (version > 0),
  description text not null,
  source_ref text,
  status text not null default 'active' check (status in ('draft', 'active', 'retired')),
  input_schema jsonb not null default '{}'::jsonb,
  steps jsonb not null default '[]'::jsonb,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (organization_id, slug, version)
);

create index if not exists ai_workflow_definitions_org_idx
  on ai_workflow_definitions (organization_id, status, slug, version desc);

create table if not exists ai_workflow_runs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  workspace_id uuid references workspaces(id) on delete set null,
  definition_id uuid not null references ai_workflow_definitions(id) on delete restrict,
  requested_by uuid references users(id) on delete set null,
  approved_by uuid references users(id) on delete set null,
  status text not null default 'pending_approval'
    check (status in ('pending_approval', 'ready', 'running', 'completed', 'failed', 'cancelled')),
  idempotency_key text not null,
  input jsonb not null default '{}'::jsonb,
  output jsonb,
  current_step_key text,
  estimated_cost_cents bigint check (estimated_cost_cents is null or estimated_cost_cents >= 0),
  actual_cost_cents bigint not null default 0 check (actual_cost_cents >= 0),
  currency varchar(3) not null default 'BRL',
  approved_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, idempotency_key)
);

create index if not exists ai_workflow_runs_org_idx
  on ai_workflow_runs (organization_id, created_at desc);

create table if not exists ai_workflow_step_runs (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references ai_workflow_runs(id) on delete cascade,
  step_key text not null,
  position integer not null check (position >= 0),
  name text not null,
  interactive boolean not null default false,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'waiting_approval', 'completed', 'failed', 'skipped')),
  provider text,
  model text,
  input jsonb not null default '{}'::jsonb,
  output jsonb,
  cost_cents bigint check (cost_cents is null or cost_cents >= 0),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, step_key)
);

create index if not exists ai_workflow_step_runs_run_idx
  on ai_workflow_step_runs (run_id, position);

create table if not exists ai_usage_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  workspace_id uuid references workspaces(id) on delete set null,
  workflow_run_id uuid references ai_workflow_runs(id) on delete set null,
  user_id uuid references users(id) on delete set null,
  provider text not null,
  model text,
  source text not null,
  external_event_id text,
  input_units bigint check (input_units is null or input_units >= 0),
  output_units bigint check (output_units is null or output_units >= 0),
  cached_units bigint check (cached_units is null or cached_units >= 0),
  unit text not null default 'tokens',
  cost_cents bigint check (cost_cents is null or cost_cents >= 0),
  currency varchar(3) not null default 'USD',
  metadata jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create unique index if not exists ai_usage_events_external_id_idx
  on ai_usage_events (organization_id, provider, external_event_id)
  where external_event_id is not null;

create index if not exists ai_usage_events_org_period_idx
  on ai_usage_events (organization_id, occurred_at desc);
