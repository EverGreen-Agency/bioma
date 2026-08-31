-- Planejador compartilhado: contrato/briefing -> plano aprovado -> fases e entregas.
create table if not exists project_plans (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  source_contract_id uuid references project_contracts(id) on delete set null,
  version integer not null check (version > 0),
  discipline text not null check (discipline in ('social', 'growth', 'tech', 'general')),
  source_kind text not null check (source_kind in ('contract', 'briefing', 'onboarding', 'manual')),
  status text not null default 'draft'
    check (status in ('draft', 'approved', 'materialized', 'superseded')),
  generation_mode text not null default 'manual'
    check (generation_mode in ('live', 'preview', 'manual')),
  title text not null,
  objective text,
  assumptions jsonb not null default '[]'::jsonb,
  created_by uuid references users(id) on delete set null,
  approved_by uuid references users(id) on delete set null,
  approved_at timestamptz,
  materialized_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, version)
);

create table if not exists project_plan_items (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references project_plans(id) on delete cascade,
  sequence integer not null check (sequence > 0),
  source_scope_item_id uuid references contract_scope_items(id) on delete set null,
  phase_name text not null,
  title text not null,
  description text,
  item_kind text not null
    check (item_kind in ('milestone', 'deliverable', 'content', 'campaign', 'technical_task')),
  due_offset_days integer check (due_offset_days is null or due_offset_days between 0 and 730),
  client_visible boolean not null default true,
  approval_required boolean not null default true,
  github_eligible boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  materialized_phase_id uuid references project_phases(id) on delete set null,
  materialized_deliverable_id uuid references deliverables(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (plan_id, sequence)
);

create index if not exists project_plans_project_idx
  on project_plans (project_id, version desc);

create index if not exists project_plan_items_plan_idx
  on project_plan_items (plan_id, sequence);

create or replace function enforce_project_plan_scope()
returns trigger
language plpgsql
as $$
declare
  expected_discipline text;
  contract_project uuid;
begin
  select project_type into expected_discipline from projects where id = new.project_id;
  if expected_discipline is distinct from new.discipline then
    raise exception 'Disciplina do plano precisa corresponder ao tipo do projeto.';
  end if;
  if new.source_contract_id is not null then
    select project_id into contract_project from project_contracts where id = new.source_contract_id;
    if contract_project is distinct from new.project_id then
      raise exception 'Contrato de origem precisa pertencer ao projeto do plano.';
    end if;
  end if;
  return new;
end
$$;

drop trigger if exists project_plan_scope_guard on project_plans;
create trigger project_plan_scope_guard
before insert or update on project_plans
for each row execute function enforce_project_plan_scope();

create or replace function enforce_project_plan_item_scope()
returns trigger
language plpgsql
as $$
declare
  plan_project uuid;
  scope_project uuid;
begin
  if new.source_scope_item_id is null then return new; end if;
  select project_id into plan_project from project_plans where id = new.plan_id;
  select contract.project_id into scope_project
  from contract_scope_items scope
  join project_contracts contract on contract.id = scope.contract_id
  where scope.id = new.source_scope_item_id;
  if plan_project is distinct from scope_project then
    raise exception 'Item de escopo precisa pertencer ao projeto do plano.';
  end if;
  return new;
end
$$;

drop trigger if exists project_plan_item_scope_guard on project_plan_items;
create trigger project_plan_item_scope_guard
before insert or update on project_plan_items
for each row execute function enforce_project_plan_item_scope();

alter table workspace_squad_definitions
  drop constraint if exists workspace_squad_definitions_pilar_check;

alter table workspace_squad_definitions
  add constraint workspace_squad_definitions_pilar_check
    check (pilar in ('oferta', 'demanda', 'conversao', 'onboarding', 'planning'));

alter table workspace_squad_executions
  drop constraint if exists workspace_squad_executions_pilar_check;

alter table workspace_squad_executions
  add constraint workspace_squad_executions_pilar_check
    check (pilar in ('oferta', 'demanda', 'conversao', 'onboarding', 'planning'));
