-- Memória persistente para o copiloto/agentes, inspirada no Hermes Agent
-- (SOUL.md/MEMORY.md/skills), adaptada para software de agência multi-tenant:
--
-- - `workspace_id` NULL = memória GLOBAL da EG (identidade do copiloto,
--   aprendizados cross-cliente); preenchido = memória daquele workspace.
-- - Toda escrita gera uma revisão em `agent_memory_revisions` — auditoria de
--   quem (humano ou o próprio agente) mudou o quê e por quê.
-- - Skills propostas pelo agente nascem `pending_review`: só entram no
--   contexto do copiloto depois de um admin EG aprovar (decisão do Eduardo,
--   2026-07-30 — mesma cautela já aplicada a ação visível ao cliente).

create table if not exists agent_memories (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id) on delete cascade,
  category text not null check (category in ('identity', 'fact', 'preference', 'directive')),
  title text not null check (char_length(title) between 2 and 200),
  body text not null check (char_length(body) between 1 and 4000),
  -- NULL = escrito pelo próprio agente; preenchido = humano. Proveniência
  -- precisa ser visível na tela, não só auditável no log.
  authored_by uuid references users(id) on delete set null,
  status text not null default 'active' check (status in ('active', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_agent_memories_scope
  on agent_memories (workspace_id, category, status);

create table if not exists agent_memory_revisions (
  id uuid primary key default gen_random_uuid(),
  memory_id uuid not null references agent_memories(id) on delete cascade,
  action text not null check (action in ('created', 'updated', 'archived', 'restored')),
  previous_body text,
  new_body text,
  -- NULL = ação do agente. Toda revisão registra o motivo — é o que torna
  -- "ver o que melhorou" possível sem adivinhar pelo diff puro.
  actor_user_id uuid references users(id) on delete set null,
  reason text not null check (char_length(reason) between 1 and 500),
  created_at timestamptz not null default now()
);

create index if not exists idx_agent_memory_revisions_memory
  on agent_memory_revisions (memory_id, created_at desc);

create table if not exists agent_skills (
  id uuid primary key default gen_random_uuid(),
  -- NULL = skill utilizável em qualquer workspace (procedimento genérico);
  -- preenchido = específica daquele cliente/operação.
  workspace_id uuid references workspaces(id) on delete cascade,
  name text not null check (char_length(name) between 2 and 120),
  -- "Level 0" do Hermes: sempre visível ao modelo, decide se carrega o resto.
  description text not null check (char_length(description) between 2 and 300),
  -- "Level 1": o procedimento completo, carregado só quando referenciado.
  procedure text not null check (char_length(procedure) between 1 and 6000),
  status text not null default 'pending_review'
    check (status in ('pending_review', 'approved', 'rejected', 'retired')),
  -- NULL = proposta pelo próprio copiloto durante uma conversa.
  proposed_by uuid references users(id) on delete set null,
  source_context text,
  reviewed_by uuid references users(id) on delete set null,
  reviewed_at timestamptz,
  review_note text,
  use_count int not null default 0,
  last_used_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_agent_skills_scope
  on agent_skills (workspace_id, status);
