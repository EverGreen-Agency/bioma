-- Migration 0061: Google Business Profile (Negócios Locais), Google AdSense e
-- YouTube orgânico — reaproveitam o mesmo service account/API key do Google já
-- usado por GA4/GTM/Search Console (business.manage e adsense.readonly são
-- escopos adicionais do mesmo GOOGLE_SERVICE_ACCOUNT_JSON).

create table if not exists workspace_business_profile_daily_metrics (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  date date not null,
  location_id text not null,
  impressions_maps bigint not null default 0,
  impressions_search bigint not null default 0,
  website_clicks bigint not null default 0,
  call_clicks bigint not null default 0,
  direction_requests bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, location_id, date)
);

create index if not exists workspace_business_profile_daily_workspace_date_idx
  on workspace_business_profile_daily_metrics (workspace_id, date desc);

create table if not exists workspace_adsense_daily_metrics (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  date date not null,
  account_id text not null,
  estimated_earnings_cents bigint not null default 0,
  page_views bigint not null default 0,
  clicks bigint not null default 0,
  impressions bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, account_id, date)
);

create index if not exists workspace_adsense_daily_workspace_date_idx
  on workspace_adsense_daily_metrics (workspace_id, date desc);

create table if not exists workspace_youtube_organic_videos (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  video_id text not null,
  channel_id text not null,
  title text,
  published_at timestamptz,
  view_count bigint not null default 0,
  like_count bigint not null default 0,
  comment_count bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, video_id)
);

create index if not exists workspace_youtube_organic_videos_workspace_idx
  on workspace_youtube_organic_videos (workspace_id, published_at desc);
