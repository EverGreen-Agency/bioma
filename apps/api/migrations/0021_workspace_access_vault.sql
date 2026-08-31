-- Cofre de acessos por workspace: metadados consultáveis, segredos cifrados pela API.

create table if not exists vault_credentials (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  platform text not null,
  label text not null,
  account_hint text,
  visibility text not null default 'internal' check (visibility in ('internal', 'client')),
  status text not null default 'active'
    check (status in ('active', 'expired', 'rotating', 'compromised', 'revoked')),
  encrypted_username text,
  encrypted_password text,
  encrypted_token text,
  encrypted_recovery_codes text,
  encrypted_notes text,
  expires_at timestamptz,
  owner_user_id uuid references users(id) on delete set null,
  created_by uuid references users(id) on delete set null,
  updated_by uuid references users(id) on delete set null,
  version integer not null default 1 check (version > 0),
  last_rotated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint vault_has_secret_check check (
    encrypted_username is not null
    or encrypted_password is not null
    or encrypted_token is not null
    or encrypted_recovery_codes is not null
    or encrypted_notes is not null
  )
);

create index if not exists vault_credentials_workspace_idx
  on vault_credentials (workspace_id, status, updated_at desc);

create index if not exists vault_credentials_tenant_idx
  on vault_credentials (tenant_organization_id, workspace_id);

create or replace function enforce_vault_workspace_tenant()
returns trigger
language plpgsql
as $$
declare
  workspace_tenant uuid;
begin
  select tenant_organization_id into workspace_tenant
  from workspaces
  where id = new.workspace_id;

  if workspace_tenant is null or workspace_tenant is distinct from new.tenant_organization_id then
    raise exception 'Credencial e workspace precisam pertencer ao mesmo tenant.';
  end if;
  return new;
end
$$;

drop trigger if exists vault_workspace_tenant_guard on vault_credentials;
create trigger vault_workspace_tenant_guard
before insert or update on vault_credentials
for each row execute function enforce_vault_workspace_tenant();
