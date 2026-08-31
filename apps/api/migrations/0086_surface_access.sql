-- Acesso e visibilidade por superfície: equipe, usuário e preferência pessoal.
--
-- Decisão 11 (2026-08-06). Havia dois eixos e nenhum alcançava o admin da EG:
-- `enabled_modules` (o cliente contratou?) e `organization_feature_flags` (isto
-- está pronto para este cliente?). Ambos param na organização. Faltavam os
-- sujeitos do meio — a equipe e a pessoa — e o eixo mais fraco de todos, que
-- não é permissão nenhuma: "eu não uso isso agora".
--
-- Duas tabelas porque são duas naturezas, e fundi-las seria o erro:
--
-- - `surface_grants` é PERMISSÃO. Vale contra o usuário mesmo que ele discorde,
--   e para cliente é proibição de verdade (o backend recusa a rota, não só
--   esconde o botão).
-- - `surface_preferences` é ORGANIZAÇÃO DE TELA. É do dono, ele liga e desliga
--   à vontade, e não protege nada.
--
-- A regra que não pode depender de código para valer: **preferência só
-- esconde, nunca concede.** Por isso `hidden` tem `check (hidden)` — o banco
-- recusa fisicamente uma linha de preferência que tente liberar acesso. Se um
-- bug futuro tentar usar esta tabela para conceder, ele falha na escrita, não
-- em produção com a porta aberta.
--
-- O catálogo de superfícies fica em `bioma_api/surfaces.py`, como o de feature
-- flags: uma superfície existe porque uma rota existe. Aqui só moram exceções.

create table if not exists surface_grants (
  id uuid primary key default gen_random_uuid(),

  -- Sem FK para um catálogo: as chaves vivem em código. Uma superfície
  -- removida deixa linhas órfãs, que a resolução simplesmente ignora (a
  -- listagem administrativa as mostra como "superfície desconhecida" para
  -- alguém limpar) — melhor que impedir o deploy de uma rota aposentada.
  surface_key text not null,

  -- Exatamente um sujeito. Mesmo padrão de `workspace_assignments` (0014).
  team_id uuid references teams(id) on delete cascade,
  user_id uuid references users(id) on delete cascade,

  -- `deny` tira; `allow` devolve o que um nível mais amplo tirou. `allow`
  -- nunca ultrapassa o teto da organização — isso é regra de resolução, não
  -- de esquema, e está testada em test_surface_access.py.
  effect text not null check (effect in ('allow', 'deny')),

  -- O motivo aparece na tela de quem perdeu o acesso. "Herdado da equipe
  -- Growth" responde a pergunta; um 403 seco gera chamado.
  note text,

  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint surface_grants_one_subject_check check (
    (team_id is not null and user_id is null)
    or (team_id is null and user_id is not null)
  )
);

create unique index if not exists surface_grants_team_idx
  on surface_grants (team_id, surface_key)
  where team_id is not null;

create unique index if not exists surface_grants_user_idx
  on surface_grants (user_id, surface_key)
  where user_id is not null;

create index if not exists surface_grants_user_lookup_idx on surface_grants (user_id);
create index if not exists surface_grants_team_lookup_idx on surface_grants (team_id);

create table if not exists surface_preferences (
  user_id uuid not null references users(id) on delete cascade,
  surface_key text not null,

  -- `check (hidden)` é o ponto inteiro desta tabela: preferência que concede
  -- acesso não pode nem ser gravada. Mostrar de novo é apagar a linha, não
  -- gravar `false` — assim "ver de novo" volta a herdar o nível de cima em vez
  -- de fixar um `true` que mascara uma mudança de permissão posterior.
  hidden boolean not null default true check (hidden),

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  primary key (user_id, surface_key)
);
