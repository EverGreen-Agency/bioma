create table if not exists client_files (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  visibility text not null default 'client' check (visibility in ('internal', 'client')),
  file_name text not null,
  content_type text not null,
  size_bytes bigint not null,
  storage_key text not null unique,
  uploaded_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists client_files_org_created_idx on client_files (organization_id, created_at desc);
