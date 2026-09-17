-- Benchmark público: fonte, consentimento e toggle.
--
-- Princípio: o Bioma é a fonte da verdade; agrega e anonimiza no backend.
-- O site só lê o endpoint público /public/benchmark. Nada de cliente
-- individual sai daqui — só agregados por segmento com k-anonimato.

-- 1) Consentimento e segmento por organização (cliente).
--    Só entra no benchmark quem consentiu explicitamente E tem segmento.
alter table organizations
  add column if not exists benchmark_segment text,
  add column if not exists benchmark_consent boolean not null default false;

-- 2) Scores do Raio-X Comercial (fonte dos agregados).
--    Três pilares (Oferta/Demanda/Conversão), nota 0–10, por avaliação.
--    A agregação usa a avaliação mais recente de cada organização.
--    (A UI de preenchimento do Raio-X é Fase 2; a tabela já existe para
--     o benchmark ter fonte real e para receber os scores quando chegar.)
create table if not exists raio_x_scores (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  assessed_at date not null default current_date,
  pillar text not null check (pillar in ('oferta', 'demanda', 'conversao')),
  score numeric(4, 2) not null check (score >= 0 and score <= 10),
  level text not null default 'fundacional' check (level in ('fundacional', 'otimizacao')),
  created_at timestamptz not null default now(),
  unique (organization_id, assessed_at, pillar)
);

create index if not exists raio_x_scores_org_assessed_idx
  on raio_x_scores (organization_id, assessed_at desc);

-- 3) Toggle global do benchmark público (singleton).
--    status = 'em_breve' | 'ao_vivo'; o site sai do "Em Breve" sozinho
--    quando isto vira 'ao_vivo' — sem redeploy, sem hardcode.
--    min_sample = k-anonimato: mínimo de organizações por segmento.
create table if not exists benchmark_settings (
  id boolean primary key default true check (id),
  status text not null default 'em_breve' check (status in ('em_breve', 'ao_vivo')),
  min_sample integer not null default 5 check (min_sample >= 3),
  updated_at timestamptz not null default now()
);

insert into benchmark_settings (id) values (true)
  on conflict (id) do nothing;
