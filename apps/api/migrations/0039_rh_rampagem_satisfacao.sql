-- MOD-RH-001 (Fase 4 do PLANO-MESTRE): rampagem de funcionários (marcos de
-- 15/30/60/90 dias, configuráveis por tenant — não hardcoded por cargo) e
-- satisfação/NPS por workspace, para compor a carteira/performance de gestor
-- junto com os projetos que ele já gerencia (workspace_assignments).

create table if not exists onboarding_milestone_templates (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  day_offset integer not null check (day_offset >= 0),
  title text not null,
  description text,
  status text not null default 'active' check (status in ('active', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists onboarding_milestone_templates_tenant_idx
  on onboarding_milestone_templates (tenant_organization_id, status, day_offset);

create table if not exists employee_onboarding_plans (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  hire_date date not null,
  -- [{"template_id": "<uuid>"|null, "day_offset": 15, "title": "...", "status": "pending"|"done", "completed_at": null}]
  -- snapshot no momento da criação: mudar um template depois não altera planos já emitidos.
  milestones jsonb not null default '[]'::jsonb,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_organization_id, user_id)
);

create table if not exists workspace_satisfaction_scores (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  score numeric(4,1) not null check (score >= 0 and score <= 10),
  source text not null default 'manual',
  notes text,
  captured_at timestamptz not null default now(),
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists workspace_satisfaction_scores_workspace_idx
  on workspace_satisfaction_scores (workspace_id, captured_at desc);
