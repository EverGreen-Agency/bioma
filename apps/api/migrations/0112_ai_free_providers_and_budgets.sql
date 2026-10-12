-- Migração 0112: Provedores Gratuitos (FreeLLMAPI Nativo) e Gestão Granular de Orçamentos de IA

CREATE TABLE IF NOT EXISTS ai_provider_key_pool (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid REFERENCES organizations(id) ON DELETE CASCADE,
    provider_code varchar(64) NOT NULL,
    label varchar(128) NOT NULL DEFAULT 'Chave Padrão',
    key_encrypted text NOT NULL,
    key_fingerprint varchar(32) NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'active',
    error_count int NOT NULL DEFAULT 0,
    last_used_at timestamptz,
    last_error_at timestamptz,
    last_error_message text,
    cooldown_until timestamptz,
    call_count bigint NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_provider_key_pool_provider
    ON ai_provider_key_pool (provider_code, status);

CREATE INDEX IF NOT EXISTS idx_ai_provider_key_pool_org
    ON ai_provider_key_pool (organization_id);

CREATE TABLE IF NOT EXISTS ai_organization_budgets (
    organization_id uuid PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    monthly_token_cap bigint,
    monthly_cost_cap_cents int,
    alert_threshold_percent int NOT NULL DEFAULT 80,
    enforce_hard_stop boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
