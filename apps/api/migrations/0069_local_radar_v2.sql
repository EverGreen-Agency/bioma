-- Radar Local v2: import de planilha (extensão de scrape do Eduardo) e
-- histórico de mudanças por place_id entre scans (rescan detecta "criou site",
-- "nota mudou" — o sinal barato e legal de que o negócio começou a investir).

alter table local_radar_scans
  add column if not exists source text not null default 'places'
    check (source in ('places', 'import'));

alter table local_radar_prospects
  add column if not exists changes jsonb not null default '[]'::jsonb;
