-- Fila editorial do blog da EG.
--
-- Por que tabela propria e nao `artifacts`: artifact exige `organization_id` —
-- e peca DE cliente. Post do blog da EG nao tem cliente. E nao cabe em
-- `eg_knowledge_docs` porque aquilo alimenta o copiloto: misturar rascunho de
-- marketing com base de conhecimento polui a fonte que o copiloto consulta.
--
-- O que justifica os campos de SEO aqui: a auditoria de 28/08/2026 mostrou o
-- dominio com 16 keywords, zero no top 10 e trafego organico estimado zero.
-- Os 12 posts do calendario existem para atacar keywords especificas com volume
-- verificado — guardar a keyword-alvo junto do texto e o que impede o proximo
-- post de ser escrito por intuicao.
--
-- Publicacao continua sendo pelo caminho que ja existe: `cms.py` monta o payload
-- do WordPress a partir do texto. Esta tabela e o antes, nao o depois.

create table if not exists eg_blog_posts (
  id uuid primary key default gen_random_uuid(),

  slug  text not null unique,
  title text not null,
  excerpt text,
  content text not null,

  -- alvo de busca, do calendario editorial
  target_keyword text,
  search_volume  int,
  difficulty     int,
  intent         text,
  planned_month  text,          -- 'YYYY-MM', a fatia do calendario

  status text not null default 'draft'
    check (status in ('draft', 'review', 'approved', 'published', 'archived')),

  -- preenchido quando sai para o WordPress pelo caminho do cms.py
  published_url text,
  published_at  timestamptz,

  seeded     boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by uuid references users(id) on delete set null
);

create index if not exists eg_blog_posts_status_idx on eg_blog_posts (status, planned_month);
