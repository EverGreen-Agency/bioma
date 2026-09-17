-- Snapshot GitHub confirmado vira atualização compreensível no projeto/hub.
create table if not exists project_github_activity_syncs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  idempotency_key text not null unique,
  snapshot jsonb not null,
  project_update_id uuid not null references project_updates(id) on delete cascade,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  check (jsonb_typeof(snapshot) = 'object')
);

create index if not exists project_github_activity_syncs_project_idx
  on project_github_activity_syncs (project_id, created_at desc);
