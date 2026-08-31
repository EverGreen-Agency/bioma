-- Migration 0063: RD Station CRM e HubSpot — CRMs adicionais além do Kommo.
--
-- Ambos autenticam por token estático por conta (não OAuth com refresh), então
-- reaproveitam performance_connections com o token cifrado em metadata, igual
-- ao TikTok/LinkedIn da 0062. Uma única tabela de negociações serve aos dois
-- (e a futuros CRMs) com a coluna `source` discriminando a origem — evita
-- multiplicar tabela por fornecedor de CRM.

create table if not exists workspace_crm_deals (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  source text not null check (source in ('rd_station_crm', 'hubspot')),
  external_deal_id text not null,
  name text,
  amount_cents bigint not null default 0,
  currency text not null default 'BRL',
  stage text,
  pipeline text,
  status text not null default 'open' check (status in ('open', 'won', 'lost')),
  owner_name text,
  external_created_at timestamptz,
  external_closed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, source, external_deal_id)
);

create index if not exists workspace_crm_deals_workspace_idx
  on workspace_crm_deals (workspace_id, source, external_created_at desc);

create index if not exists workspace_crm_deals_status_idx
  on workspace_crm_deals (workspace_id, status);
