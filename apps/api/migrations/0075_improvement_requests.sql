-- Requisições de melhoria propostas pelo copiloto.
--
-- É o "Caminho B" do desenho: quando o copiloto percebe que o cliente precisa
-- de algo que **não existe no catálogo** (um tipo de widget novo, um módulo),
-- ele não pode montar sozinho — então registra uma requisição com evidência.
--
-- Por que não vai direto para o Banco de Ideias: lá é funil de ideia
-- estratégica, sem prazo nem dono; uma requisição concreta morreria no meio de
-- 149 ideias. E por que não nasce como tarefa: antes de virar trabalho ela
-- precisa da sua revisão.
--
-- Ciclo: `pending` → (aprovar) vira TAREFA e status `converted`
--                  → (rejeitar) status `rejected`.
-- A fila é caixa de entrada (transitória); a tarefa é o trabalho (persistente).
-- Nunca os dois ao mesmo tempo — aprovar é o que tira da fila.

create table if not exists improvement_requests (
  id uuid primary key default gen_random_uuid(),
  -- Cliente que originou. NULL = melhoria da própria operação EG.
  workspace_id uuid references workspaces(id) on delete cascade,
  title text not null check (char_length(title) between 2 and 200),
  -- O que o cliente precisa, em termos de resultado — não de implementação.
  need text not null check (char_length(need) between 2 and 4000),
  -- O que o copiloto tentou montar com o catálogo atual e por que não deu.
  -- É isto que separa "requisição com evidência" de "ideia solta".
  evidence text,
  -- `client_deliverable` decide onde a tarefa nasce: entrega esperada pelo
  -- cliente vai visível no board dele; melhoria interna nasce escondida.
  client_deliverable boolean not null default false,
  status text not null default 'pending'
    check (status in ('pending', 'converted', 'rejected')),
  -- NULL = proposta pelo próprio copiloto.
  proposed_by uuid references users(id) on delete set null,
  reviewed_by uuid references users(id) on delete set null,
  reviewed_at timestamptz,
  review_note text,
  -- Preenchido na conversão: para onde a requisição foi.
  task_id uuid references eg_tasks(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_improvement_requests_status
  on improvement_requests (status, created_at desc);
