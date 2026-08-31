-- Decisões de escopo 2026-07-14 (ROADMAP-MVP.md):
-- multi-tenant flat preparado para hierarquia white-label, feature-gating
-- por organização e convite de usuário cliente por link (AUTH-001).

alter table organizations
  add column if not exists parent_organization_id uuid references organizations(id) on delete set null;

alter table organizations
  add column if not exists enabled_modules jsonb not null default '["hub", "content", "files"]'::jsonb;

-- A organização EG opera a plataforma: enxerga tudo.
update organizations
set enabled_modules = '["hub", "content", "files", "commercial", "analytics", "integrations", "engineering"]'::jsonb
where type = 'eg';

create table if not exists invites (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  role text not null default 'client_user' check (role in ('client_user')),
  email text,
  token_hash text not null unique,
  expires_at timestamptz not null,
  used_at timestamptz,
  used_by uuid references users(id) on delete set null,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists invites_org_created_idx on invites (organization_id, created_at desc);
