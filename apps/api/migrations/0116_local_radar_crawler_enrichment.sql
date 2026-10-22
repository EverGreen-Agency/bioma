-- Radar Local: enriquecimento autônomo via web crawler (estilo Google Maps Scraper Kit).
-- Permite que prospects minerados tenham seus websites navegados em busca de
-- e-mails corporativos e perfis de redes sociais (Instagram, Facebook, LinkedIn).

alter table local_radar_prospects
  add column if not exists emails jsonb not null default '[]'::jsonb,
  add column if not exists social_links jsonb not null default '{}'::jsonb,
  add column if not exists crawler_status text not null default 'pending'
    check (crawler_status in ('pending', 'running', 'completed', 'failed', 'no_website')),
  add column if not exists crawler_error text,
  add column if not exists enriched_at timestamptz;

create index if not exists idx_local_radar_prospects_crawler on local_radar_prospects (crawler_status);
