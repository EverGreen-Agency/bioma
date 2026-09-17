create table if not exists kommo_integrations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null unique references organizations(id) on delete cascade,
  client_id text not null,
  client_secret text not null,
  integration_id text,
  access_token text,
  refresh_token text,
  subdomain text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists kommo_metrics_snapshots (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  pipeline_id text not null,
  pipeline_name text not null,
  snapshot_date date not null default current_date,
  total_leads int not null default 0,
  won_leads int not null default 0,
  lost_leads int not null default 0,
  active_leads int not null default 0,
  total_value numeric(14, 2) not null default 0,
  won_value numeric(14, 2) not null default 0,
  created_at timestamptz not null default now(),
  unique (organization_id, pipeline_id, snapshot_date)
);
