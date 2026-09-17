-- 0042_opportunity_platform_configs.sql
-- Tabela para gerenciar conexões, RSS customizados, tokens e custos financeiros de plataformas de prospecção/freelancer.

create table if not exists opportunity_platform_configs (
    id uuid primary key default gen_random_uuid(),
    platform_key varchar(50) not null unique,
    platform_name varchar(100) not null,
    status varchar(20) not null default 'active', -- 'active', 'paused', 'not_configured'
    rss_url text,
    api_key_or_token text,
    monthly_cost_cents bigint not null default 0,
    notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_opp_platform_key on opportunity_platform_configs(platform_key);
