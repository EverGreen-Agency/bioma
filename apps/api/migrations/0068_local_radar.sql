-- Radar Local: prospecção de negócios locais via Google Places + auditoria de
-- presença digital + fila de aprovação humana antes de qualquer outbound.
-- Nenhum prospect vira contato sem review_status = 'approved' por um humano.

create table if not exists local_radar_scans (
  id uuid primary key default gen_random_uuid(),
  created_by uuid references users(id) on delete set null,
  niche text not null,
  city text not null,
  query_text text not null,
  status text not null default 'completed' check (status in ('completed', 'failed')),
  error_message text,
  prospect_count int not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists local_radar_prospects (
  id uuid primary key default gen_random_uuid(),
  scan_id uuid not null references local_radar_scans(id) on delete cascade,
  place_id text not null,
  name text not null,
  address text,
  phone text,
  website text,
  google_maps_url text,
  rating numeric(2,1),
  rating_count int,
  business_status text,
  place_types text[] not null default '{}',
  -- Score determinístico (0-100) e lacunas calculados só dos campos reais do
  -- Places; a IA nunca altera esses valores.
  presence_score int,
  presence_gaps jsonb not null default '[]'::jsonb,
  audit jsonb,
  audit_mode text check (audit_mode in ('live', 'preview')),
  outreach_message text,
  review_status text not null default 'new'
    check (review_status in ('new', 'audited', 'approved', 'rejected', 'sent')),
  reviewed_by uuid references users(id) on delete set null,
  reviewed_at timestamptz,
  lead_id uuid references leads(id) on delete set null,
  sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (scan_id, place_id)
);

create index if not exists idx_local_radar_prospects_scan on local_radar_prospects (scan_id);
create index if not exists idx_local_radar_prospects_review on local_radar_prospects (review_status);
