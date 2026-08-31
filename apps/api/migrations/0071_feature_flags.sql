-- Feature flags por organização.
--
-- `enabled_modules` (que já existe) responde "o cliente contratou este módulo?".
-- Isto responde outra pergunta: "esta feature já está pronta para este cliente?".
-- São eixos diferentes — um cliente pode ter o módulo `analytics` contratado e
-- mesmo assim ver o Radar Local como "em breve".
--
-- Sem linha na tabela, vale o default declarado em código (`FEATURE_CATALOG`),
-- então nenhuma feature depende de seed para funcionar.

create table if not exists organization_feature_flags (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  feature_key text not null check (char_length(feature_key) between 2 and 80),
  state text not null check (state in ('hidden', 'coming_soon', 'beta', 'active')),
  -- Motivo é obrigatório para forçar registro de decisão: "por que este cliente
  -- vê beta" é a pergunta que ninguém lembra 3 meses depois.
  note text,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, feature_key)
);

create index if not exists idx_org_feature_flags_org
  on organization_feature_flags (organization_id);
