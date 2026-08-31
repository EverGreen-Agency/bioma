alter table sync_runs
  add column if not exists client_id uuid references clients(id) on delete cascade,
  add column if not exists provider text,
  add column if not exists date_from date,
  add column if not exists date_to date,
  add column if not exists records_processed integer not null default 0,
  add column if not exists error_code text,
  add column if not exists error_message text;

alter table sync_runs drop constraint if exists sync_runs_status_check;
alter table sync_runs
  add constraint sync_runs_status_check
  check (status in ('queued', 'running', 'ok', 'error', 'partial'));

create index if not exists sync_runs_client_provider_started_idx
  on sync_runs (client_id, provider, started_at desc);

create table if not exists performance_connections (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete cascade,
  organization_id uuid not null references organizations(id) on delete cascade,
  provider text not null check (provider in ('google_ads', 'ga4', 'search_console', 'gtm')),
  external_account_id text not null,
  external_parent_id text,
  display_name text,
  status text not null default 'active' check (status in ('active', 'inactive', 'error')),
  credentials_ref text,
  last_synced_at timestamptz,
  last_error_at timestamptz,
  last_error_message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_id, provider, external_account_id)
);

create index if not exists performance_connections_org_provider_idx
  on performance_connections (organization_id, provider);

create table if not exists monthly_targets (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete cascade,
  organization_id uuid not null references organizations(id) on delete cascade,
  month date not null,
  budget_micros bigint,
  target_conversions numeric,
  target_cpa_micros bigint,
  target_roas numeric,
  target_leads numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_id, month)
);

create table if not exists ads_campaign_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  customer_id text not null,
  campaign_id text not null,
  campaign_name text not null,
  campaign_status text not null,
  channel_type text not null,
  budget_micros bigint,
  impressions bigint not null default 0,
  clicks bigint not null default 0,
  cost_micros bigint not null default 0,
  conversions numeric not null default 0,
  all_conversions numeric not null default 0,
  conversion_value numeric not null default 0,
  search_impression_share numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, campaign_id)
);

create table if not exists ads_keyword_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  campaign_id text not null,
  campaign_name text not null,
  ad_group_id text not null,
  ad_group_name text not null,
  criterion_id text not null,
  keyword_text text not null,
  match_type text not null,
  status text not null,
  impressions bigint not null default 0,
  clicks bigint not null default 0,
  cost_micros bigint not null default 0,
  conversions numeric not null default 0,
  conversion_value numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, criterion_id)
);

create table if not exists ads_search_term_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  campaign_id text not null,
  campaign_name text not null,
  ad_group_id text not null,
  ad_group_name text not null,
  search_term text not null,
  targeting_status text,
  impressions bigint not null default 0,
  clicks bigint not null default 0,
  cost_micros bigint not null default 0,
  conversions numeric not null default 0,
  conversion_value numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, campaign_id, ad_group_id, search_term)
);

create table if not exists ads_segment_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  campaign_id text not null,
  segment_type text not null,
  segment_value text not null,
  impressions bigint not null default 0,
  clicks bigint not null default 0,
  cost_micros bigint not null default 0,
  conversions numeric not null default 0,
  conversion_value numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, campaign_id, segment_type, segment_value)
);

create table if not exists ads_conversion_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  conversion_action_id text not null,
  conversion_action_name text not null,
  conversion_category text,
  conversions numeric not null default 0,
  all_conversions numeric not null default 0,
  conversion_value numeric not null default 0,
  cost_micros bigint,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, conversion_action_id)
);

create table if not exists ga4_acquisition_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  source text not null,
  medium text not null,
  campaign text not null,
  sessions bigint not null default 0,
  total_users bigint not null default 0,
  new_users bigint not null default 0,
  engaged_sessions bigint not null default 0,
  engagement_rate numeric not null default 0,
  key_events numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, source, medium, campaign)
);

create table if not exists ga4_landing_page_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  landing_page text not null,
  sessions bigint not null default 0,
  total_users bigint not null default 0,
  engaged_sessions bigint not null default 0,
  engagement_rate numeric not null default 0,
  average_session_duration numeric not null default 0,
  screen_page_views bigint not null default 0,
  key_events numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, landing_page)
);

create table if not exists ga4_event_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  event_name text not null,
  event_count bigint not null default 0,
  total_users bigint not null default 0,
  key_events numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, event_name)
);

create table if not exists ga4_device_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  device_category text not null,
  sessions bigint not null default 0,
  total_users bigint not null default 0,
  engaged_sessions bigint not null default 0,
  key_events numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, device_category)
);

create table if not exists gsc_query_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  query text not null,
  country text not null,
  device text not null,
  clicks numeric not null default 0,
  impressions numeric not null default 0,
  ctr numeric not null default 0,
  position numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, query, country, device)
);

create table if not exists gsc_page_daily (
  client_id uuid not null references clients(id) on delete cascade,
  date date not null,
  page text not null,
  country text not null,
  device text not null,
  clicks numeric not null default 0,
  impressions numeric not null default 0,
  ctr numeric not null default 0,
  position numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (client_id, date, page, country, device)
);

create table if not exists gtm_audit_snapshots (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete cascade,
  collected_at timestamptz not null default now(),
  account_id text not null,
  container_id text not null,
  workspace_id text,
  published_version text,
  tags jsonb not null default '[]'::jsonb,
  triggers jsonb not null default '[]'::jsonb,
  variables jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists tracking_findings (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete cascade,
  snapshot_id uuid not null references gtm_audit_snapshots(id) on delete cascade,
  code text not null,
  title text not null,
  description text not null,
  severity text not null check (severity in ('info', 'low', 'medium', 'high', 'critical')),
  status text not null default 'open' check (status in ('open', 'resolved', 'ignored')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table if not exists performance_insights (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete cascade,
  source text not null,
  category text not null,
  severity text not null check (severity in ('info', 'warning', 'critical')),
  title text not null,
  description text not null,
  recommendation text,
  period_start date not null,
  period_end date not null,
  current_value numeric,
  comparison_value numeric,
  status text not null default 'active' check (status in ('active', 'archived', 'resolved')),
  generated_by text not null default 'system',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists analyst_actions (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete cascade,
  created_by uuid references users(id) on delete set null,
  action_date date not null default current_date,
  title text not null,
  description text not null,
  expected_result text,
  status text not null default 'pending' check (status in ('pending', 'completed', 'cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ads_campaign_daily_client_date_idx on ads_campaign_daily (client_id, date);
create index if not exists ads_keyword_daily_client_date_idx on ads_keyword_daily (client_id, date);
create index if not exists ads_search_term_daily_client_date_idx on ads_search_term_daily (client_id, date);
create index if not exists ads_segment_daily_client_date_idx on ads_segment_daily (client_id, date);
create index if not exists ads_conversion_daily_client_date_idx on ads_conversion_daily (client_id, date);
create index if not exists ga4_acquisition_daily_client_date_idx on ga4_acquisition_daily (client_id, date);
create index if not exists ga4_landing_page_daily_client_date_idx on ga4_landing_page_daily (client_id, date);
create index if not exists ga4_event_daily_client_date_idx on ga4_event_daily (client_id, date);
create index if not exists ga4_device_daily_client_date_idx on ga4_device_daily (client_id, date);
create index if not exists gsc_query_daily_client_date_idx on gsc_query_daily (client_id, date);
create index if not exists gsc_page_daily_client_date_idx on gsc_page_daily (client_id, date);
create index if not exists gtm_audit_snapshots_client_collected_idx on gtm_audit_snapshots (client_id, collected_at desc);
create index if not exists tracking_findings_client_status_idx on tracking_findings (client_id, status);
create index if not exists performance_insights_client_period_idx on performance_insights (client_id, period_start, period_end);
create index if not exists analyst_actions_client_status_idx on analyst_actions (client_id, status);
create index if not exists gtm_audit_snapshots_tags_idx on gtm_audit_snapshots using gin (tags);
create index if not exists gtm_audit_snapshots_triggers_idx on gtm_audit_snapshots using gin (triggers);
create index if not exists gtm_audit_snapshots_variables_idx on gtm_audit_snapshots using gin (variables);

create or replace view vw_performance_source_freshness as
select
  client_id,
  provider,
  status,
  last_synced_at,
  last_error_at,
  last_error_message
from performance_connections;

create or replace view vw_ads_account_summary as
select
  client_id,
  sum(impressions)::bigint as total_impressions,
  sum(clicks)::bigint as total_clicks,
  sum(cost_micros)::bigint as total_cost_micros,
  sum(conversions)::numeric as total_conversions,
  sum(conversion_value)::numeric as total_conversion_value
from ads_campaign_daily
group by client_id;

create or replace view vw_budget_pacing as
with current_month_spend as (
  select
    client_id,
    date_trunc('month', date)::date as month,
    sum(cost_micros)::bigint as actual_spend_micros,
    count(distinct date)::integer as days_elapsed
  from ads_campaign_daily
  where date >= date_trunc('month', current_date)::date
    and date <= current_date
  group by client_id, date_trunc('month', date)::date
)
select
  t.client_id,
  t.month,
  t.budget_micros,
  coalesce(s.actual_spend_micros, 0) as actual_spend_micros,
  coalesce(s.days_elapsed, 0) as days_elapsed,
  extract(day from (date_trunc('month', t.month) + interval '1 month' - interval '1 day'))::integer as total_days_in_month,
  case
    when coalesce(s.days_elapsed, 0) > 0 then
      ((coalesce(s.actual_spend_micros, 0)::numeric / s.days_elapsed) *
       extract(day from (date_trunc('month', t.month) + interval '1 month' - interval '1 day')))::bigint
    else 0::bigint
  end as projected_spend_micros
from monthly_targets t
left join current_month_spend s on t.client_id = s.client_id and t.month = s.month;
