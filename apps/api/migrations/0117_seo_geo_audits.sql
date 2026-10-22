-- Migration 0117: Auditoria de SEO Técnico e GEO (Generative Engine Optimization)
-- Baseado na metodologia de ponta do Claude-SEO (E-E-A-T, Schema.org, llms.txt e AI Search Readiness).

CREATE TABLE IF NOT EXISTS workspace_seo_geo_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tenant_organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    target_url TEXT NOT NULL,
    page_title VARCHAR(500),
    seo_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    geo_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    
    -- Diagnóstico On-Page / Técnico (Title, Description, Canonical, H1..H6, Links, Imagens sem Alt)
    technical_audit JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Diagnóstico GEO (llms.txt status, Schemas JSON-LD detectados, densidade de fatos, sinais E-E-A-T)
    geo_audit JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Gerador automatizado com 1 clique de llms.txt para motores generativos (Perplexity, ChatGPT, Claude)
    generated_llms_txt TEXT,
    
    -- Schema.org / JSON-LD recomendado estruturado para injeção no head do site
    generated_schema_jsonld JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Sinalização de WAF ativo (Cloudflare/Incapsula) com bypass gracioso
    waf_detected BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_seo_geo_audits_workspace ON workspace_seo_geo_audits(workspace_id);
CREATE INDEX IF NOT EXISTS idx_seo_geo_audits_tenant ON workspace_seo_geo_audits(tenant_organization_id);
CREATE INDEX IF NOT EXISTS idx_seo_geo_audits_created_at ON workspace_seo_geo_audits(created_at DESC);
