-- Pesquisa de mercado versionada, rastreável e isolada por workspace.
create table if not exists market_researches (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  subject_organization_id uuid not null references organizations(id) on delete cascade,
  version integer not null check (version > 0),
  sector text not null check (char_length(sector) between 2 and 120),
  geographic_scope text not null default 'Brasil',
  objective text,
  selected_focus jsonb not null default '[]'::jsonb,
  status text not null default 'running'
    check (status in ('running', 'completed', 'failed', 'archived')),
  generation_mode text not null default 'manual'
    check (generation_mode in ('live', 'preview', 'manual')),
  provider text,
  model text,
  provider_response_id text,
  report jsonb,
  token_usage jsonb not null default '{}'::jsonb,
  estimated_cost_cents integer check (estimated_cost_cents is null or estimated_cost_cents >= 0),
  source_count integer not null default 0 check (source_count >= 0),
  client_visible boolean not null default false,
  error_message text,
  created_by uuid references users(id) on delete set null,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, version)
);

create table if not exists market_research_sources (
  id uuid primary key default gen_random_uuid(),
  research_id uuid not null references market_researches(id) on delete cascade,
  url text not null,
  title text,
  publisher text,
  publication_date date,
  consulted_at timestamptz not null default now(),
  unique (research_id, url)
);

create index if not exists market_researches_workspace_idx
  on market_researches (workspace_id, version desc);

create index if not exists market_research_sources_research_idx
  on market_research_sources (research_id);

create or replace function enforce_market_research_workspace_scope()
returns trigger
language plpgsql
as $$
declare
  expected_tenant uuid;
  expected_subject uuid;
begin
  select tenant_organization_id, subject_organization_id
    into expected_tenant, expected_subject
  from workspaces
  where id = new.workspace_id and status = 'active';

  if expected_tenant is null
    or expected_tenant is distinct from new.tenant_organization_id
    or expected_subject is distinct from new.subject_organization_id then
    raise exception 'Pesquisa precisa permanecer no tenant e workspace de origem.';
  end if;
  return new;
end
$$;

drop trigger if exists market_research_workspace_scope_guard on market_researches;
create trigger market_research_workspace_scope_guard
before insert or update on market_researches
for each row execute function enforce_market_research_workspace_scope();
