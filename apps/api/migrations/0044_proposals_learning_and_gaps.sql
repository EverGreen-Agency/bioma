-- 0044_proposals_learning_and_gaps.sql
-- Tabelas para inventario de competencias, gaps de tecnologia e cases injetados nas propostas.

create table if not exists tech_skill_inventory (
    id uuid primary key default gen_random_uuid(),
    skill_name varchar(100) not null unique,
    category varchar(50) not null default 'general', -- 'crm', 'ads', 'automation', 'dev', 'analytics'
    status varchar(20) not null default 'available', -- 'available', 'wanted', 'in_progress'
    case_count integer not null default 1,
    notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists opportunity_skill_gaps (
    id uuid primary key default gen_random_uuid(),
    opportunity_id uuid references opportunity_radar(id) on delete cascade,
    missing_skill varchar(100) not null,
    impact_level varchar(20) not null default 'high', -- 'high', 'medium', 'low'
    opportunity_title text not null,
    opportunity_url text,
    status varchar(20) not null default 'open', -- 'open', 'resolved', 'ignored'
    created_at timestamptz not null default now()
);

-- Adicionar colunas de cases injetados e feedback de win/loss nas propostas
alter table commercial_proposals add column if not exists attached_cases jsonb default '[]'::jsonb;
alter table commercial_proposals add column if not exists win_loss_feedback text;

-- Seed inicial de competencias disponiveis na EG
insert into tech_skill_inventory (skill_name, category, status, case_count, notes)
values
    ('Meta Ads', 'ads', 'available', 12, 'Campanha de tráfego pago e remarketing para aquisição B2B'),
    ('Google Ads', 'ads', 'available', 10, 'Rede de pesquisa, PMax e anúncios de intenção de busca'),
    ('React & Next.js', 'dev', 'available', 15, 'Desenvolvimento de dashboards e webapps de alta conversão'),
    ('FastAPI & Python', 'dev', 'available', 14, 'Automação de APIs, scrapers e pipelines de dados'),
    ('n8n & Webhooks', 'automation', 'available', 8, 'Automação de fluxos de CRM e acompanhamento de leads'),
    ('WhatsApp API / Evolution', 'automation', 'available', 9, 'Regras de mensagens e atendimento automatizado'),
    ('Landing Pages de Alta Conversão', 'conversao', 'available', 18, 'Páginas otimizadas para captura de leads e vendas B2B')
on conflict (skill_name) do nothing;
