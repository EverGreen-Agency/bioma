-- MOD-BI-SOCIAL-001: habilita meta_ads/linkedin_ads como providers de
-- performance_connections. As tabelas de métrica diária (0032) e o restante
-- do pipeline de sync (sync_runs, upsert_rows) já são genéricos por provider
-- — só o check constraint da lista de providers válidos precisava mudar.

alter table performance_connections drop constraint if exists performance_connections_provider_check;
alter table performance_connections
  add constraint performance_connections_provider_check
  check (provider in ('google_ads', 'ga4', 'search_console', 'gtm', 'meta_ads', 'linkedin_ads'));

-- storage.upsert_rows() sempre grava updated_at no conflito; as duas tabelas
-- de 0032 nasceram sem essa coluna, o que quebraria a sincronização real.
alter table workspace_meta_ads_daily_metrics add column if not exists updated_at timestamptz not null default now();
alter table workspace_linkedin_ads_daily_metrics add column if not exists updated_at timestamptz not null default now();
