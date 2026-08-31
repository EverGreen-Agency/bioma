-- Base de conhecimento da EG sai do disco e vai para o banco.
--
-- Problema que isto resolve: Banco de Ideias, Banco de Stack, Arquitetura e
-- Engenharia liam arquivos de `_opensquad/_memory/` em runtime. O Dockerfile da
-- API usa `bioma/apps/api/` como contexto de build, então esses arquivos NUNCA
-- existiram em staging/produção — as telas apareciam vazias e a escrita
-- respondia 503. Eram features que só funcionavam na máquina de quem
-- desenvolve.
--
-- Com os dados aqui: as telas funcionam em qualquer ambiente, o copiloto passa
-- a conseguir ler ideias/stack/arquitetura como dossiê, e o repositório pode
-- ser limpo sem quebrar nada.
--
-- Volume: os JSON estruturados somam ~120 KB e os markdown ~4 MB. Binário
-- (PDF do manual de marca, inputs) NÃO entra aqui — vai para o storage de
-- arquivos que já existe.

create table if not exists eg_ideas (
  id uuid primary key default gen_random_uuid(),
  -- Identificador legível herdado do arquivo (ex: "mod-multitenant"). É por ele
  -- que as ideias se referenciam entre si em `part_of` / `depends_on`.
  slug text not null unique check (char_length(slug) between 1 and 120),
  title text not null,
  description text,
  category text,
  stage text,
  horizon text,
  origin text,
  source text,
  readiness text,
  -- Composição entre ideias (umbrella -> partes) e dependências, guardadas como
  -- slug para sobreviver a reimportação.
  part_of text,
  depends_on text[] not null default '{}',
  enables text[] not null default '{}',
  archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_eg_ideas_stage on eg_ideas (stage) where archived = false;

create table if not exists eg_stack_techs (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (char_length(slug) between 1 and 120),
  name text not null,
  -- Modelo ThoughtWorks: assess / trial / adopt / hold.
  ring text not null,
  quadrant text not null,
  note text,
  adr text,
  source text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_eg_stack_ring on eg_stack_techs (ring, quadrant);

-- Documentos de conhecimento (markdown). Guardados como texto porque são KB,
-- precisam de busca e são lidos junto com o resto do dossiê — mandar para o
-- storage transformaria cada leitura em ida à rede e mataria a busca.
create table if not exists eg_knowledge_docs (
  id uuid primary key default gen_random_uuid(),
  -- Caminho relativo de origem, usado como chave de reimportação idempotente.
  path text not null unique check (char_length(path) between 1 and 500),
  category text not null check (category in ('knowledge', 'engineering', 'architecture', 'company')),
  title text not null,
  content text not null,
  -- `seeded` distingue "veio do import inicial" de "escrito aqui dentro": o
  -- seeder só sobrescreve o que ele mesmo semeou, nunca edição humana.
  seeded boolean not null default true,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_eg_knowledge_category on eg_knowledge_docs (category);
