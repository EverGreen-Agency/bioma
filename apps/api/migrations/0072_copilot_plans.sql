-- Planos multi-etapa do copiloto.
--
-- Por que existe: o copiloto executava UMA ação por mensagem. Os casos reais do
-- Eduardo ("cadastrar cliente novo", "roteiro para os próximos anúncios",
-- "participar do hackathon X") são sequências de 4-8 ações que dependem umas
-- das outras.
--
-- `ai_workflow_runs` já fazia multi-etapa com checkpoint humano, mas suas etapas
-- produzem TEXTO — descrevem o que fazer, não executam. Isto é a ponte: etapas
-- que executam ações reais do catálogo do copiloto, com o humano aprovando o
-- plano inteiro antes de qualquer coisa rodar.
--
-- Regra central: um plano nasce `pending_approval`. Nenhuma etapa executa antes
-- da aprovação — nem as reversíveis. Aprovar o plano é aprovar a sequência.

create table if not exists copilot_plans (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id) on delete cascade,
  created_by uuid not null references users(id) on delete cascade,
  goal text not null check (char_length(goal) between 2 and 2000),
  summary text not null,
  status text not null default 'pending_approval'
    check (status in ('pending_approval', 'approved', 'running', 'completed', 'failed', 'rejected', 'cancelled')),
  -- Quantas etapas exigem confirmação individual (ação visível ao cliente).
  -- Aprovar o plano NÃO aprova essas — elas param e pedem de novo.
  requires_confirmation_count int not null default 0,
  approved_by uuid references users(id) on delete set null,
  approved_at timestamptz,
  finished_at timestamptz,
  error_message text,
  generation_mode text not null default 'live' check (generation_mode in ('live', 'preview')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_copilot_plans_status on copilot_plans (status, created_at desc);
create index if not exists idx_copilot_plans_workspace on copilot_plans (workspace_id, created_at desc);

create table if not exists copilot_plan_steps (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references copilot_plans(id) on delete cascade,
  position int not null check (position >= 0),
  action_name text not null,
  label text not null,
  params jsonb not null default '{}'::jsonb,
  why text not null default '',
  -- `blocked` = ação visível ao cliente que precisa de confirmação própria,
  -- mesmo com o plano aprovado.
  status text not null default 'pending'
    check (status in ('pending', 'running', 'executed', 'failed', 'skipped', 'blocked')),
  detail text,
  undo_hint text,
  executed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (plan_id, position)
);

create index if not exists idx_copilot_plan_steps_plan on copilot_plan_steps (plan_id, position);
