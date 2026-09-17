-- MOD-CERTIFICACOES-001 (Fase 4 do PLANO-MESTRE): certificações de
-- funcionários (Google Ads, Meta Blueprint, HubSpot...) e da própria EG
-- (ex. Google Partner) — user_id nulo indica certificação da agência.

create table if not exists certifications (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  user_id uuid references users(id) on delete cascade,
  provider text not null,
  name text not null,
  credential_id text,
  verification_url text,
  issued_at date not null,
  expires_at date,
  notes text,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists certifications_tenant_idx on certifications (tenant_organization_id, expires_at);
create index if not exists certifications_user_idx on certifications (user_id);
