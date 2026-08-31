-- Migration 0032: Meta Ads & LinkedIn Ads Daily Performance Metrics

create table if not exists workspace_meta_ads_daily_metrics (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  date date not null,
  account_id text,
  account_name text,
  campaign_id text,
  campaign_name text,
  impressions bigint not null default 0,
  clicks bigint not null default 0,
  spend_cents bigint not null default 0,
  conversions integer not null default 0,
  leads integer not null default 0,
  revenue_cents bigint not null default 0,
  created_at timestamptz not null default now(),
  unique (workspace_id, campaign_id, date)
);

create index if not exists workspace_meta_ads_daily_workspace_date_idx
  on workspace_meta_ads_daily_metrics (workspace_id, date desc);

create table if not exists workspace_linkedin_ads_daily_metrics (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  date date not null,
  account_id text,
  account_name text,
  campaign_id text,
  campaign_name text,
  impressions bigint not null default 0,
  clicks bigint not null default 0,
  spend_cents bigint not null default 0,
  conversions integer not null default 0,
  leads integer not null default 0,
  revenue_cents bigint not null default 0,
  created_at timestamptz not null default now(),
  unique (workspace_id, campaign_id, date)
);

create index if not exists workspace_linkedin_ads_daily_workspace_date_idx
  on workspace_linkedin_ads_daily_metrics (workspace_id, date desc);
