-- Conversa contínua com o copiloto + trilha auditável de cada execução.
--
-- Duas necessidades que caem na mesma estrutura:
--
-- 1) O copiloto precisa ser um interlocutor fixo, não um formulário de pergunta
--    solta. Sem thread, cada mensagem começa do zero e ele nunca "percorre a
--    operação com você".
--
-- 2) Precisamos poder auditar o que ele fez: quais fontes leu, quais memórias e
--    habilidades entraram no dossiê, quanto custou, quanto demorou, e se a
--    resposta veio do modelo ou de prévia local. Sem isso, "ele disse que fez"
--    é indistinguível de "ele fez".
--
-- Por que não reusar `ai_runs` / `ai_workflow_step_runs`: aquelas tabelas são do
-- plano de controle de IA (workflows com roteamento, cota e aprovação por etapa)
-- e estão vazias — nada escreve nelas hoje. Forçar o copiloto lá dentro pagaria
-- o preço do modelo de workflow sem usar nada dele. Estas aqui são estreitas e
-- escritas em toda chamada.

create table if not exists copilot_threads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  -- Escopo em que a conversa nasceu. Mantido na thread para o copiloto saber
  -- de onde ela veio mesmo que você navegue para outra tela.
  surface text not null,
  workspace_id uuid references workspaces(id) on delete cascade,
  task_id uuid references eg_tasks(id) on delete set null,
  title text,
  status text not null default 'active' check (status in ('active', 'archived')),
  last_message_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists copilot_threads_user_idx
  on copilot_threads (user_id, status, last_message_at desc);

create table if not exists copilot_runs (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references copilot_threads(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  surface text not null,
  workspace_id uuid references workspaces(id) on delete cascade,
  task_id uuid references eg_tasks(id) on delete set null,

  message text not null,
  answer text,
  confidence text,
  -- `live` = veio do modelo. `preview` = prévia local sem OPENAI_API_KEY.
  -- Guardado por execução porque a mesma thread pode ter as duas coisas.
  generation_mode text,
  provider text,
  model text,
  status text not null default 'running' check (status in ('running', 'completed', 'failed')),
  error_message text,

  -- O que entrou no contexto. Não é o dossiê inteiro (que pode ser grande e
  -- conter dado de cliente): é o índice do que foi lido, para você conferir a
  -- procedência sem a trilha virar uma segunda cópia do banco.
  dossier_summary jsonb not null default '{}'::jsonb,
  memories_used jsonb not null default '[]'::jsonb,
  skills_used jsonb not null default '[]'::jsonb,
  sources jsonb not null default '[]'::jsonb,
  actions jsonb not null default '[]'::jsonb,

  input_tokens integer,
  output_tokens integer,
  cost_cents integer,
  duration_ms integer,

  created_at timestamptz not null default now()
);

create index if not exists copilot_runs_thread_idx on copilot_runs (thread_id, created_at);
create index if not exists copilot_runs_user_idx on copilot_runs (user_id, created_at desc);

-- Etapas dentro de uma execução: montar dossiê, chamar o modelo, executar cada
-- ação. É o que responde "em que ele gastou o tempo" e "onde falhou".
create table if not exists copilot_run_steps (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references copilot_runs(id) on delete cascade,
  position integer not null,
  kind text not null check (kind in ('dossier', 'plan', 'action', 'persist')),
  label text not null,
  status text not null check (status in ('ok', 'skipped', 'blocked', 'failed')),
  detail text,
  payload jsonb not null default '{}'::jsonb,
  duration_ms integer,
  created_at timestamptz not null default now()
);

create index if not exists copilot_run_steps_run_idx on copilot_run_steps (run_id, position);
