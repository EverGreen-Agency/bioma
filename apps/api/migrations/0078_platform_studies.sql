-- Estudo de plataformas: build vs. buy vs. parar de construir.
--
-- A pergunta que motiva a tabela não é "quais ferramentas existem". É:
-- desta plataforma, eu assino, integro, absorvo para o Bioma, compro, ou ela é
-- sinal de que eu deveria PARAR de construir o Bioma? A última é a que importa
-- e a que ninguém registra em lugar nenhum — some numa aba do navegador.
--
-- Por que não reusar `market_researches`: aquilo é pesquisa de SETOR para um
-- cliente, com escopo de workspace e visibilidade para o cliente. Isto é
-- decisão interna da EG sobre o próprio produto. Compartilham a forma (rodar
-- IA, guardar fonte, contar token) e nada do significado.

create table if not exists platform_studies (
  id uuid primary key default gen_random_uuid(),

  url text not null unique,
  -- Nome derivado do domínio até a pesquisa achar o nome real. Nunca fica vazio:
  -- lista de 78 URLs crus é ilegível.
  name text not null,
  -- Para qual frente estamos avaliando. Uma plataforma pode servir a mais de uma.
  targets jsonb not null default '["bioma"]'::jsonb,
  added_note text,

  -- ---- o que a pesquisa descobriu (nulo até rodar) ----
  research_status text not null default 'pending'
    check (research_status in ('pending', 'researching', 'researched', 'failed')),
  research_error text,
  category text,
  one_liner text,
  pricing_summary text,
  -- Estruturado: o que faz, para quem, o que tem que o Bioma não tem, o que o
  -- Bioma tem que ela não tem.
  findings jsonb not null default '{}'::jsonb,
  -- URLs realmente buscadas. Sem isto a análise é opinião do modelo sobre o
  -- nome do domínio.
  sources jsonb not null default '[]'::jsonb,
  -- Imagem que a própria empresa escolheu para se representar (og:image).
  -- Não é screenshot: é o que ela publica como cartão. Honesto e sem browser.
  preview_image_url text,

  -- ---- o julgamento ----
  -- 0-100: quanto do que a plataforma faz o Bioma já faz ou pretende fazer.
  overlap_score integer check (overlap_score between 0 and 100),
  -- Quão forte é o sinal de "pare de construir isto".
  threat_level text check (threat_level in ('nenhuma', 'baixa', 'media', 'alta', 'critica')),
  -- Fila de teste manual: nem toda plataforma merece uma tarde de avaliação.
  test_priority integer,

  -- ---- a decisão, que é humana ----
  verdict text check (verdict in (
    'assinar',      -- vale pagar e usar como está
    'integrar',     -- conectar via API, sem reconstruir
    'absorver',     -- remodelar a ideia dentro do Bioma
    'comprar',      -- vale procurar aquisição
    'monitorar',    -- ainda não, mas de olho
    'descartar',    -- não serve
    'repensar'      -- faz melhor o que o Bioma faz: rever o escopo do Bioma
  )),
  verdict_note text,
  decided_by uuid references users(id) on delete set null,
  decided_at timestamptz,

  -- ---- rastro da execução (mesmo contrato da trilha do copiloto) ----
  generation_mode text,
  provider text,
  model text,
  input_tokens integer,
  output_tokens integer,
  cost_cents integer,
  researched_at timestamptz,

  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists platform_studies_status_idx on platform_studies (research_status);
create index if not exists platform_studies_priority_idx
  on platform_studies (test_priority desc nulls last, overlap_score desc nulls last);
create index if not exists platform_studies_verdict_idx on platform_studies (verdict);
