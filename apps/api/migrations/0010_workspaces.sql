-- WORKSPACE-001: identidade operacional persistente e aditiva.
--
-- `organizations` continua sendo a fronteira física dos dados durante a
-- transição. `workspaces` passa a ser a identidade de produto/contexto e não
-- substitui ainda as FKs existentes nem as rotas baseadas em `client_id`.

alter table organizations drop constraint if exists organizations_type_check;
alter table organizations
  add constraint organizations_type_check check (type in ('eg', 'agency', 'client'));

create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete restrict,
  subject_organization_id uuid not null unique references organizations(id) on delete cascade,
  kind text not null check (kind in ('agency_internal', 'client')),
  constraint workspaces_internal_subject_check check (
    kind <> 'agency_internal' or tenant_organization_id = subject_organization_id
  ),
  name text not null,
  slug text not null,
  status text not null default 'active' check (status in ('active', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_organization_id, slug)
);

create unique index if not exists workspaces_active_internal_tenant_idx
  on workspaces (tenant_organization_id)
  where kind = 'agency_internal' and status = 'active';

create index if not exists workspaces_tenant_kind_idx
  on workspaces (tenant_organization_id, kind, status);

-- No modelo flat atual, organizações cliente sem pai pertencem à EG. Esse
-- backfill é explícito; hierarquia de autorização continua fora deste corte.
update organizations as client_org
set parent_organization_id = platform_org.id,
    updated_at = now()
from (
  select id
  from organizations
  where type = 'eg' and slug = 'eg'
  order by created_at asc
  limit 1
) as platform_org
where client_org.type = 'client'
  and client_org.parent_organization_id is null;

-- Se já havia clientes antes desta migration, não é seguro inventar um
-- tenant nem aceitar uma hierarquia circular ou cujo pai também seja cliente.
do $$
begin
  if exists (
    select 1
    from organizations child
    left join organizations tenant on tenant.id = child.parent_organization_id
    where child.type = 'client'
      and (
        tenant.id is null
        or child.parent_organization_id = child.id
        or tenant.type not in ('eg', 'agency')
      )
  ) then
    raise exception 'Organização cliente sem tenant válido (EG ou agência).';
  end if;
end $$;

insert into workspaces (
  tenant_organization_id,
  subject_organization_id,
  kind,
  name,
  slug
)
select
  o.id,
  o.id,
  'agency_internal',
  case when o.type = 'eg' then 'Operação EG' else 'Operação ' || o.name end,
  o.slug
from organizations o
where o.type in ('eg', 'agency')
on conflict (subject_organization_id) do nothing;

insert into workspaces (
  tenant_organization_id,
  subject_organization_id,
  kind,
  name,
  slug
)
select
  o.parent_organization_id,
  o.id,
  'client',
  c.name,
  o.slug
from clients c
join organizations o on o.id = c.organization_id
where o.type = 'client'
  and o.parent_organization_id is not null
on conflict (subject_organization_id) do nothing;
