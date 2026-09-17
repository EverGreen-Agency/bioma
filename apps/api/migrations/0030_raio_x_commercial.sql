-- 0030_raio_x_commercial.sql
-- Motor do Raio-X Comercial EverGreen: Oferta, Demanda, Conversao (Reguas Nivel 1 e Nivel 2)

create table if not exists workspace_commercial_scores (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null unique references workspaces(id) on delete cascade,
  oferta_score numeric(3,1) not null default 0.0,
  demanda_score numeric(3,1) not null default 0.0,
  conversao_score numeric(3,1) not null default 0.0,
  oferta_level integer not null default 1 check (oferta_level in (1, 2)),
  demanda_level integer not null default 1 check (demanda_level in (1, 2)),
  conversao_level integer not null default 1 check (conversao_level in (1, 2)),
  gargalo_prioritario text not null default 'oferta' check (gargalo_prioritario in ('oferta', 'demanda', 'conversao')),
  maturity_level text not null default 'semente' check (maturity_level in ('semente', 'muda', 'arvore', 'floresta')),
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists commercial_diagnostic_answers (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  pilar text not null check (pilar in ('oferta', 'demanda', 'conversao')),
  regua_level integer not null check (regua_level in (1, 2)),
  question_key text not null,
  score_value numeric(3,1) not null check (score_value >= 0 and score_value <= 10),
  notes text,
  updated_at timestamptz not null default now(),
  constraint unq_ws_pilar_regua_qkey unique (workspace_id, pilar, regua_level, question_key)
);

create table if not exists commercial_action_plans (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  pilar_gargalo text not null check (pilar_gargalo in ('oferta', 'demanda', 'conversao')),
  sprint_title text not null,
  sprint_goals text not null,
  status text not null default 'em_andamento' check (status in ('em_andamento', 'concluido', 'pausado')),
  start_date date not null default current_date,
  end_date date,
  created_at timestamptz not null default now()
);

create index if not exists idx_commercial_answers_ws on commercial_diagnostic_answers(workspace_id, pilar);
create index if not exists idx_commercial_plans_ws on commercial_action_plans(workspace_id);
