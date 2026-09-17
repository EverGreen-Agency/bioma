alter table project_documents
  add column if not exists contract_id uuid references project_contracts(id) on delete set null,
  add column if not exists planning_excerpt text;

create index if not exists project_documents_contract_idx
  on project_documents (contract_id, kind, created_at desc)
  where contract_id is not null;
