-- Acompanhamento transparente para projetos Tech: fases, documentos e atualizações.

create table if not exists project_phases (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  sequence integer not null check (sequence > 0),
  name text not null,
  description text,
  status text not null default 'planned'
    check (status in ('planned', 'development', 'blocked', 'internal_testing', 'client_validation', 'released')),
  client_summary text,
  client_visible boolean not null default true,
  starts_at date,
  due_at date,
  released_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, sequence)
);

create table if not exists project_documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  kind text not null check (kind in ('proposal', 'technical_spec', 'scope', 'acceptance', 'release_notes')),
  title text not null,
  url text not null,
  client_visible boolean not null default true,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, kind, url)
);

create table if not exists project_updates (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  phase_id uuid references project_phases(id) on delete set null,
  kind text not null check (kind in ('progress', 'blocker', 'testing', 'release', 'note')),
  summary text not null,
  detail text,
  client_visible boolean not null default true,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

alter table deliverables add column if not exists phase_id uuid references project_phases(id) on delete set null;

create index if not exists project_phases_project_idx on project_phases (project_id, sequence);
create index if not exists project_documents_project_idx on project_documents (project_id, kind, created_at desc);
create index if not exists project_updates_project_idx on project_updates (project_id, created_at desc);
create index if not exists deliverables_phase_idx on deliverables (phase_id, status);

create or replace function enforce_project_phase_scope()
returns trigger
language plpgsql
as $$
declare
  phase_project uuid;
begin
  if new.phase_id is null then return new; end if;
  if new.project_id is null then
    raise exception 'Entregável com fase exige projeto.';
  end if;
  select project_id into phase_project from project_phases where id = new.phase_id;
  if phase_project is distinct from new.project_id then
    raise exception 'Fase precisa pertencer ao mesmo projeto do entregável.';
  end if;
  return new;
end
$$;

drop trigger if exists deliverable_project_phase_guard on deliverables;
create trigger deliverable_project_phase_guard
before insert or update on deliverables
for each row execute function enforce_project_phase_scope();

create or replace function enforce_project_update_phase_scope()
returns trigger
language plpgsql
as $$
declare
  phase_project uuid;
begin
  if new.phase_id is null then return new; end if;
  select project_id into phase_project from project_phases where id = new.phase_id;
  if phase_project is distinct from new.project_id then
    raise exception 'Atualização precisa apontar para fase do mesmo projeto.';
  end if;
  return new;
end
$$;

drop trigger if exists project_update_phase_guard on project_updates;
create trigger project_update_phase_guard
before insert or update on project_updates
for each row execute function enforce_project_update_phase_scope();
