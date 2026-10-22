-- Migration 0115: Laboratório de Validação e Arquitetura de Ofertas (Metodologia Founder Skill)
-- Baseado nos frameworks de Alex Hormozi ($100M Offers), Peter Thiel (Zero to One) e Steve Jobs.

CREATE TABLE IF NOT EXISTS workspace_offer_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tenant_organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    product_or_service TEXT NOT NULL,
    target_audience TEXT NOT NULL,
    current_price_cents BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'reviewed', 'active', 'archived')),
    
    -- Equação de Valor de Alex Hormozi (Dream Outcome, Perceived Likelihood, Time Delay, Effort & Sacrifice)
    value_equation JSONB NOT NULL DEFAULT '{}'::jsonb,
    value_score NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    
    -- Problemas mapeados e soluções correspondentes
    problems_and_solutions JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Grand Slam Offer Stack (Core, Bônus, Garantias de Reversão de Risco, Urgência e Naming M.A.G.I.C)
    offer_stack JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Parecer do Conselho Consultivo Virtual (Lentes: Hormozi, Thiel, Jobs)
    board_verdict JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_offer_validations_workspace ON workspace_offer_validations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_offer_validations_tenant ON workspace_offer_validations(tenant_organization_id);
CREATE INDEX IF NOT EXISTS idx_offer_validations_status ON workspace_offer_validations(status);
