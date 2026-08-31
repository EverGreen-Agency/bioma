-- Migration 0034: Autonomous Squads (Oferta, Demanda, Conversão) & FinOps Token Tracking

create table if not exists workspace_squad_definitions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  pilar text not null check (pilar in ('oferta', 'demanda', 'conversao')),
  squad_slug text not null,
  squad_name text not null,
  description text,
  agents_config jsonb not null default '[]'::jsonb,
  pipeline_yaml text,
  status text not null default 'active' check (status in ('active', 'paused')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, squad_slug)
);

create table if not exists workspace_squad_executions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  squad_id uuid references workspace_squad_definitions(id) on delete set null,
  pilar text not null check (pilar in ('oferta', 'demanda', 'conversao')),
  squad_name text not null,
  triggered_by text not null default 'manual',
  status text not null default 'running' check (status in ('running', 'completed', 'failed')),
  input_data jsonb not null default '{}'::jsonb,
  output_data jsonb not null default '{}'::jsonb,
  token_usage jsonb not null default '{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}'::jsonb,
  estimated_cost_cents integer not null default 0,
  execution_logs jsonb not null default '[]'::jsonb,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists workspace_squad_exec_workspace_idx
  on workspace_squad_executions (workspace_id, started_at desc);

create index if not exists workspace_squad_exec_pilar_idx
  on workspace_squad_executions (workspace_id, pilar);
