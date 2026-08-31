-- Context Engine, Fase 1 — decisão 7.
--
-- Resposta do Eduardo: "faça para ambos" — base da EG **e** do cliente. Por isso
-- a base pende de `workspace_id`, que é o eixo que já separa os dois casos no
-- resto do sistema. Não há tipo "eg" vs "cliente": é o workspace que diz.
--
-- **Sem embeddings, de propósito (Fase 1).** A busca é lexical, no full-text do
-- Postgres. Quando a Fase 3 entrar, os mesmos fragmentos ganham vetor sem
-- precisar refragmentar — e é por isso que `knowledge_chunks` não tem nada
-- específico de busca lexical na estrutura, só o índice.

create table if not exists knowledge_bases (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,

  name text not null,
  description text,
  status text not null default 'active' check (status in ('active', 'archived')),

  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique (workspace_id, name)
);

create index if not exists knowledge_bases_workspace_idx
  on knowledge_bases (workspace_id, status);


create table if not exists knowledge_documents (
  id uuid primary key default gen_random_uuid(),
  base_id uuid not null references knowledge_bases(id) on delete cascade,

  title text not null,
  -- De onde veio. `upload` é arquivo; `text` é conteúdo colado direto, que é o
  -- caminho mais curto para a base sair do zero sem depender de storage.
  source_kind text not null default 'upload' check (source_kind in ('upload', 'text')),
  storage_key text,
  mime_type text,
  size_bytes integer,

  -- `failed` existe porque extração PODE falhar (PDF escaneado, arquivo
  -- corrompido) e o documento tem que ficar visível com o motivo. Sumir com
  -- ele faria a pessoa reenviar para sempre sem entender por quê.
  status text not null default 'pending'
    check (status in ('pending', 'indexed', 'failed')),
  failure_reason text,

  current_version integer not null default 0,
  chunks_total integer not null default 0,

  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists knowledge_documents_base_idx
  on knowledge_documents (base_id, created_at desc);


-- Versão é o texto EXTRAÍDO inteiro, não o arquivo. É contra este texto que os
-- offsets dos fragmentos apontam — sem guardá-lo, `char_start`/`char_end` não
-- teriam a que se referir e "abrir a citação na origem" viraria aproximação.
create table if not exists knowledge_document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references knowledge_documents(id) on delete cascade,
  version integer not null check (version > 0),

  extracted_text text not null,
  extracted_chars integer not null,
  -- Detecta reenvio do mesmo conteúdo: refragmentar o idêntico só gasta e
  -- muda os ids dos fragmentos sem motivo.
  checksum text not null,

  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),

  unique (document_id, version)
);


create table if not exists knowledge_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references knowledge_documents(id) on delete cascade,
  version integer not null check (version > 0),

  position integer not null check (position >= 0),
  content text not null,
  -- Trilha de títulos ancestrais, do topo até o imediato. Guardada como array
  -- porque a citação mostra o caminho inteiro: "Pelo ticket médio" sozinho não
  -- diz de qual guia veio.
  heading_path text[] not null default '{}',

  -- Offsets no texto extraído da versão. São eles que permitem abrir a origem
  -- no ponto exato em vez de rolar o documento procurando.
  char_start integer not null check (char_start >= 0),
  char_end integer not null check (char_end > char_start),

  -- Desativar em vez de apagar: o fragmento sai da busca e continua
  -- inspecionável. Apagar esconderia o motivo de a base ter respondido mal
  -- antes — que é justamente o que se quer entender ao desativar.
  is_active boolean not null default true,

  -- `simple` e não `portuguese`: o dicionário português do Postgres não vem
  -- garantido em toda instalação, e uma migração que falha por causa de
  -- configuração de texto é pior que a busca sem stemming. Trocar depois é uma
  -- migração de uma linha.
  search_vector tsvector generated always as (to_tsvector('simple', content)) stored,

  created_at timestamptz not null default now(),

  unique (document_id, version, position)
);

create index if not exists knowledge_chunks_search_idx
  on knowledge_chunks using gin (search_vector);

create index if not exists knowledge_chunks_document_idx
  on knowledge_chunks (document_id, version, position);
