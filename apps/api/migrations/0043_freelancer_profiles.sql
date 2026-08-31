-- 0043_freelancer_profiles.sql
-- Tabela para armazenamento e auditoria automatica por URL de perfis de freelancer nas plataformas.

create table if not exists freelancer_profiles (
    id uuid primary key default gen_random_uuid(),
    platform_key varchar(50) not null, -- ex: 'workana', 'upwork', '99freelas', 'linkedin', 'toptal', 'contra'
    profile_url text not null unique,
    profile_name varchar(255),
    headline text,
    bio text,
    skills jsonb default '[]'::jsonb,
    portfolio_items jsonb default '[]'::jsonb,
    audit_score integer default 0,
    audit_analysis jsonb default '{}'::jsonb,
    last_audited_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_freelancer_profiles_platform on freelancer_profiles(platform_key);
create index if not exists idx_freelancer_profiles_score on freelancer_profiles(audit_score desc);
