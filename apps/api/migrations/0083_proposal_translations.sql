-- Tradução em cache para propostas (decisão do Eduardo, 2026-08-04).
--
-- Desenho: um artefato, um idioma canônico, traduções em cache.
--
-- A proposta nasce num idioma só — o do destinatário — e é ELE que sai pelo
-- link público. O cliente nunca vê tradução; o link público não muda. A
-- tradução existe só para a equipe interna ler algo que foi gerado no idioma
-- do lead ("ver em português" quando a proposta nasceu em inglês para um lead
-- americano).
--
-- Cache por (proposta, idioma): a primeira leitura naquele idioma traduz e
-- guarda; da segunda em diante é leitura de banco, custo zero — proposta muda
-- pouco depois de enviada. Editar o original invalida TODO o cache daquela
-- proposta (todas as linhas são apagadas na próxima edição): uma tradução
-- desatualizada sendo lida como se fosse atual é pior que reprocessar.

alter table commercial_proposals
  add column if not exists content_language text not null default 'pt-BR';

create table if not exists proposal_translations (
  id uuid primary key default gen_random_uuid(),
  proposal_id uuid not null references commercial_proposals(id) on delete cascade,
  language text not null,
  title text not null,
  -- Traduz o markdown renderizado inteiro, não os campos fragmentados
  -- (scope_offer/scope_conversion/...) — é o que a pessoa de fato lê, e um
  -- blob de texto preserva a formatação sem precisar reconstruir estrutura.
  content_markdown text not null,
  generation_mode text not null check (generation_mode in ('live', 'preview')),
  provider text,
  model text,
  input_tokens integer,
  output_tokens integer,
  cost_cents integer,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (proposal_id, language)
);

create index if not exists idx_proposal_translations_proposal on proposal_translations (proposal_id);
