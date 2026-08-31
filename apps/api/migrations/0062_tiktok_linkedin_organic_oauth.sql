-- Migration 0062: TikTok orgânico, TikTok Ads e LinkedIn orgânico — as três
-- primeiras integrações a exigir OAuth por conexão (token de acesso próprio
-- por cliente, com refresh), em vez da credencial única compartilhada do
-- Google/Meta/LinkedIn Ads existentes. Tokens ficam em
-- performance_connections.metadata (cifrados, mesmo mecanismo do Kommo), sem
-- precisar de tabela nova pra isso.

create table if not exists workspace_tiktok_organic_videos (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  video_id text not null,
  title text,
  posted_at timestamptz,
  view_count bigint not null default 0,
  like_count bigint not null default 0,
  comment_count bigint not null default 0,
  share_count bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, video_id)
);

create index if not exists workspace_tiktok_organic_videos_workspace_idx
  on workspace_tiktok_organic_videos (workspace_id, posted_at desc);

create table if not exists workspace_tiktok_ads_daily_metrics (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  date date not null,
  advertiser_id text not null,
  campaign_id text,
  campaign_name text,
  impressions bigint not null default 0,
  clicks bigint not null default 0,
  spend_cents bigint not null default 0,
  conversions integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, advertiser_id, campaign_id, date)
);

create index if not exists workspace_tiktok_ads_daily_workspace_date_idx
  on workspace_tiktok_ads_daily_metrics (workspace_id, date desc);

create table if not exists workspace_linkedin_organic_daily_metrics (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  date date not null,
  organization_urn text not null,
  impressions bigint not null default 0,
  unique_impressions bigint not null default 0,
  clicks bigint not null default 0,
  likes bigint not null default 0,
  comments bigint not null default 0,
  shares bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, organization_urn, date)
);

create index if not exists workspace_linkedin_organic_daily_workspace_date_idx
  on workspace_linkedin_organic_daily_metrics (workspace_id, date desc);
