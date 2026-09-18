-- Snapshots imutáveis de métricas SEO coletadas manualmente.
create table if not exists seo_snapshots (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  source text not null check (source = 'dataforseo'),
  source_endpoint text not null,
  source_task_id text,
  target text not null,
  location_code integer not null,
  language_code text not null,
  has_data boolean not null,
  organic jsonb not null default '{}'::jsonb,
  paid jsonb not null default '{}'::jsonb,
  raw_response jsonb not null,
  response_sha256 text not null,
  cost_usd numeric(12, 6),
  measured_at timestamptz not null,
  collected_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (workspace_id, response_sha256),
  check (jsonb_typeof(organic) = 'object'),
  check (jsonb_typeof(paid) = 'object'),
  check (jsonb_typeof(raw_response) = 'object')
);

create index if not exists seo_snapshots_workspace_created_idx
  on seo_snapshots (workspace_id, created_at desc);

create or replace function reject_seo_snapshot_mutation()
returns trigger language plpgsql as $$
begin
  raise exception 'seo_snapshots são imutáveis';
end;
$$;

drop trigger if exists seo_snapshots_immutable_update on seo_snapshots;
create trigger seo_snapshots_immutable_update before update on seo_snapshots
for each row execute function reject_seo_snapshot_mutation();

drop trigger if exists seo_snapshots_immutable_delete on seo_snapshots;
create trigger seo_snapshots_immutable_delete before delete on seo_snapshots
for each row execute function reject_seo_snapshot_mutation();

comment on table seo_snapshots is
  'Snapshots append-only de leitura manual do DataForSEO; não há agendamento nem escrita no provedor.';
