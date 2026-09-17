-- 0041_freelas_propostas.sql
-- Tabela para oportunidades de projetos/freelas capturadas de plataformas externas
create table if not exists opportunity_radar (
    id uuid primary key default gen_random_uuid(),
    source_platform varchar(50) not null, -- ex: '99freelas', 'workana', 'upwork', 'weworkremotely', 'toptal'
    external_id varchar(255),
    title varchar(255) not null,
    url text,
    description text,
    budget_text varchar(100),
    fit_score integer default 0, -- 0 a 100
    fit_analysis text,
    status varchar(50) not null default 'new', -- 'new', 'qualified', 'proposal_generated', 'rejected', 'archived'
    raw_payload jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_opportunity_radar_status on opportunity_radar(status);
create index if not exists idx_opportunity_radar_fit_score on opportunity_radar(fit_score desc);
create index if not exists idx_opportunity_radar_platform on opportunity_radar(source_platform);

-- Tabela para propostas comerciais geradas e gerenciadas
create table if not exists commercial_proposals (
    id uuid primary key default gen_random_uuid(),
    opportunity_id uuid references opportunity_radar(id) on delete set null,
    client_name varchar(255) not null,
    target_niche varchar(100),
    executive_summary text not null,
    scope_offer text,      -- Pilar 1: Oferta
    scope_conversion text, -- Pilar 2: Conversão
    scope_demand text,     -- Pilar 3: Demanda
    scope_items jsonb default '[]'::jsonb,
    pricing_cents bigint not null default 0,
    delivery_days integer default 15,
    status varchar(50) not null default 'draft', -- 'draft', 'approved', 'sent', 'won', 'lost'
    public_token varchar(64) not null unique default encode(gen_random_bytes(24), 'hex'),
    created_by_user_id uuid references users(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_commercial_proposals_status on commercial_proposals(status);
create index if not exists idx_commercial_proposals_token on commercial_proposals(public_token);
