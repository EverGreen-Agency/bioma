-- mod-logistica-kits (Fase 4 do PLANO-MESTRE da mega-plataforma): controle de
-- peças físicas dos kits (fornecedor, custo, estoque), definições de kit por
-- nível de cliente, e envios/entregas por cliente.

create table if not exists kit_pieces (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  name text not null,
  supplier text,
  unit_cost_cents integer not null default 0,
  stock_qty integer not null default 0,
  status text not null default 'active' check (status in ('active', 'discontinued')),
  -- Campos de acompanhamento variam por tipo de peça (ciclos de lavagem de
  -- camiseta, durabilidade de impressão de caneca...) — flexível de propósito,
  -- não hardcoded por tipo de item.
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists kit_pieces_tenant_idx on kit_pieces (tenant_organization_id, status);

create table if not exists kit_definitions (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  name text not null,
  level text not null,
  description text,
  status text not null default 'active' check (status in ('active', 'discontinued')),
  -- [{"piece_id": "<uuid>", "quantity": 1}, ...] — composição do kit.
  pieces jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists kit_definitions_tenant_idx on kit_definitions (tenant_organization_id, status);

create table if not exists kit_shipments (
  id uuid primary key default gen_random_uuid(),
  kit_definition_id uuid not null references kit_definitions(id) on delete restrict,
  client_id uuid not null references clients(id) on delete cascade,
  status text not null default 'em_producao'
    check (status in ('em_producao', 'enviado', 'entregue', 'cancelado')),
  notes text,
  shipped_at timestamptz,
  delivered_at timestamptz,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists kit_shipments_client_idx on kit_shipments (client_id, status);
create index if not exists kit_shipments_kit_idx on kit_shipments (kit_definition_id);
