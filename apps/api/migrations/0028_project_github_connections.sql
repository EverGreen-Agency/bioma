-- Mapeamento canônico de projetos Tech para repositórios GitHub (leitura primeiro).

create table if not exists project_github_connections (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null unique references projects(id) on delete cascade,
  repository_owner text not null,
  repository_name text not null,
  default_branch text not null default 'main',
  status text not null default 'active' check (status in ('active', 'paused')),
  created_by uuid references users(id) on delete set null,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint github_repository_owner_check check (repository_owner ~ '^[A-Za-z0-9_.-]+$'),
  constraint github_repository_name_check check (repository_name ~ '^[A-Za-z0-9_.-]+$')
);

create index if not exists project_github_connections_repository_idx
  on project_github_connections (repository_owner, repository_name);
