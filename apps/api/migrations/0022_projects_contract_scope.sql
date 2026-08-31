-- Motor nativo de projetos: contrato -> escopo -> entregáveis -> aceite.

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  organization_id uuid not null references organizations(id) on delete cascade,
  name text not null,
  code text,
  project_type text not null default 'general' check (project_type in ('social', 'growth', 'tech', 'general')),
  status text not null default 'planned'
    check (status in ('planned', 'active', 'on_hold', 'completed', 'cancelled', 'archived')),
  owner_user_id uuid references users(id) on delete set null,
  start_at date,
  due_at date,
  cadence_days integer check (cadence_days is null or cadence_days > 0),
  client_visible boolean not null default true,
  objective text,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, code)
);

create table if not exists project_contracts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  version integer not null default 1 check (version > 0),
  title text not null,
  status text not null default 'draft'
    check (status in ('draft', 'pending_signature', 'active', 'expired', 'terminated', 'superseded')),
  starts_at date,
  ends_at date,
  total_value numeric(14, 2),
  currency text not null default 'BRL',
  source_provider text,
  external_id text,
  signed_at timestamptz,
  client_visible boolean not null default true,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, version)
);

create table if not exists contract_scope_items (
  id uuid primary key default gen_random_uuid(),
  contract_id uuid not null references project_contracts(id) on delete cascade,
  title text not null,
  description text,
  quantity numeric(12, 2) not null default 1 check (quantity > 0),
  unit text not null default 'entrega',
  cadence text not null default 'one_off'
    check (cadence in ('one_off', 'weekly', 'biweekly', 'monthly', 'quarterly', 'custom')),
  cadence_days integer check (cadence_days is null or cadence_days > 0),
  acceptance_required boolean not null default true,
  acceptance_criteria text,
  client_visible boolean not null default true,
  status text not null default 'active' check (status in ('active', 'paused', 'removed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table deliverables add column if not exists project_id uuid references projects(id) on delete set null;
alter table deliverables add column if not exists scope_item_id uuid references contract_scope_items(id) on delete set null;
alter table deliverables add column if not exists completed_at timestamptz;

alter table eg_task_lists add column if not exists project_id uuid references projects(id) on delete set null;

create index if not exists projects_workspace_idx on projects (workspace_id, status, updated_at desc);
create index if not exists project_contracts_project_idx on project_contracts (project_id, version desc);
create index if not exists contract_scope_items_contract_idx on contract_scope_items (contract_id, status);
create index if not exists deliverables_project_idx on deliverables (project_id, status, due_at);
create index if not exists deliverables_scope_idx on deliverables (scope_item_id, status);
create index if not exists eg_task_lists_project_idx on eg_task_lists (project_id);

create or replace function enforce_project_workspace_scope()
returns trigger
language plpgsql
as $$
declare
  workspace_tenant uuid;
  workspace_subject uuid;
begin
  select tenant_organization_id, subject_organization_id
    into workspace_tenant, workspace_subject
  from workspaces where id = new.workspace_id;
  if workspace_tenant is distinct from new.tenant_organization_id
     or workspace_subject is distinct from new.organization_id then
    raise exception 'Projeto precisa pertencer ao tenant e organização do workspace.';
  end if;
  return new;
end
$$;

drop trigger if exists project_workspace_scope_guard on projects;
create trigger project_workspace_scope_guard
before insert or update on projects
for each row execute function enforce_project_workspace_scope();

create or replace function enforce_deliverable_project_scope()
returns trigger
language plpgsql
as $$
declare
  project_org uuid;
  scope_project uuid;
begin
  if new.project_id is null and new.scope_item_id is null then return new; end if;
  if new.project_id is null then raise exception 'Entregável com item de escopo exige projeto.'; end if;
  select organization_id into project_org from projects where id = new.project_id;
  if project_org is distinct from new.organization_id then
    raise exception 'Entregável e projeto precisam pertencer à mesma organização.';
  end if;
  if new.scope_item_id is not null then
    select contract.project_id into scope_project
    from contract_scope_items scope
    join project_contracts contract on contract.id = scope.contract_id
    where scope.id = new.scope_item_id;
    if scope_project is distinct from new.project_id then
      raise exception 'Item de escopo precisa pertencer ao mesmo projeto do entregável.';
    end if;
  end if;
  return new;
end
$$;

drop trigger if exists deliverable_project_scope_guard on deliverables;
create trigger deliverable_project_scope_guard
before insert or update on deliverables
for each row execute function enforce_deliverable_project_scope();

create or replace function maintain_deliverable_completed_at()
returns trigger
language plpgsql
as $$
begin
  if new.status = 'done' then
    new.completed_at = coalesce(new.completed_at, now());
  else
    new.completed_at = null;
  end if;
  return new;
end
$$;

drop trigger if exists deliverable_completed_at_guard on deliverables;
create trigger deliverable_completed_at_guard
before insert or update of status on deliverables
for each row execute function maintain_deliverable_completed_at();
