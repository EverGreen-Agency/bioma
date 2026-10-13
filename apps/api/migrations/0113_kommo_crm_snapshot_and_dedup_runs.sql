-- Painel de dados reais do Kommo e histórico de deduplicação.
--
-- kommo_crm_snapshots guarda a última leitura do CRM por organização em formato
-- compacto e SEM dado pessoal (nada de nome, telefone ou e-mail): só datas, etapa,
-- valor e os campos de classificação. É o que alimenta o painel sem bater na API
-- do Kommo a cada visita.
--
-- kommo_dedup_runs guarda cada varredura de duplicatas com o relatório completo.
-- O relatório tem nome de contato, então a leitura é restrita a EG admin no serviço.

create table if not exists kommo_crm_snapshots (
  organization_id uuid primary key references organizations(id) on delete cascade,
  subdomain text not null,
  leads_count int not null default 0,
  pipelines jsonb not null default '[]'::jsonb,
  leads jsonb not null default '[]'::jsonb,
  fetched_by uuid references users(id) on delete set null,
  fetched_at timestamptz not null default now()
);

create table if not exists kommo_dedup_runs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  requested_by uuid references users(id) on delete set null,
  subdomain text not null,
  contacts_scanned int not null default 0,
  clusters_count int not null default 0,
  duplicates_count int not null default 0,
  leads_to_reassign int not null default 0,
  clusters_applied int not null default 0,
  report jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists kommo_dedup_runs_org_created_idx
  on kommo_dedup_runs (organization_id, created_at desc);
