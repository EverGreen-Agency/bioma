-- Memória por natureza, não por quem escreveu (decisão do Eduardo, 2026-08-04).
--
-- O caso que motiva: alguém diz ao copiloto "a Univet vence o contrato em
-- março, e me responda sempre sem introdução" — uma frase, duas naturezas.
-- "Responda sem introdução" é preferência de quem falou. "A Univet vence em
-- março" é fato da empresa e não pode depender de quem perguntou.
--
-- `owner_user_id` é o escopo pessoal. Só pode existir em `category = 'preference'`
-- — o CHECK abaixo impede um fato ou diretriz virar segredo pessoal por
-- acidente. Memória pessoal só entra no dossiê de quem é dono dela; memória
-- compartilhada (owner nulo) continua visível a todo mundo, como sempre foi.

alter table agent_memories
  add column if not exists owner_user_id uuid references users(id) on delete cascade;

alter table agent_memories
  add constraint agent_memories_owner_only_preference
  check (owner_user_id is null or category = 'preference');

create index if not exists idx_agent_memories_owner on agent_memories (owner_user_id) where owner_user_id is not null;
