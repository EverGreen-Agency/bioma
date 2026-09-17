-- Wiki EG: base de conhecimento interna da agência (manuais, playbooks,
-- metodologia). Antes disto a tela `Wiki EG` era um stub estático sem backend.
--
-- Conteúdo vive como markdown no Postgres (funciona em produção, diferente do
-- backoffice que lê o monorepo `_opensquad/` só existente em dev). Anexos
-- binários (PDF/DOCX/...) ficam no S3 via storage.py, com metadados aqui.
--
-- Escopo: tenant da agência (organização EG). Só platform_admin acessa.

create table if not exists wiki_documents (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  category text not null default 'geral'
    check (category in ('comercial', 'rh', 'operacao', 'geral')),
  title text not null,
  content text not null default '',
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists wiki_documents_tenant_category_idx
  on wiki_documents (tenant_organization_id, category, updated_at desc);

create table if not exists wiki_attachments (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references wiki_documents(id) on delete cascade,
  file_name text not null,
  storage_key text not null,
  content_type text not null default 'application/octet-stream',
  size_bytes bigint not null default 0,
  uploaded_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists wiki_attachments_document_idx
  on wiki_attachments (document_id, created_at desc);
