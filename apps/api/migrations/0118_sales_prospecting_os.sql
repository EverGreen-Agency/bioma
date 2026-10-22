-- Migration 0118: Sales & Prospecting OS (Fila de Prospecção, Sessões de Foco, Sales Knowledge Cards e Handoff Estruturado)
-- Baseado na especificação canônica do Bioma Sales & Prospecting OS v0.1 e EverGreen Sales Content Spec v0.1.

-- 1. Tabela de Conhecimento Comercial (Playbooks, Objeções, Battlecards, Princípios, Sinais e Scripts)
CREATE TABLE IF NOT EXISTS sales_knowledge_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE, -- NULL representa card global do Bioma / EverGreen
    code VARCHAR(20) NOT NULL, -- Ex: C001, C025, BC01, PB01
    slug VARCHAR(150) NOT NULL,
    title VARCHAR(255) NOT NULL,
    card_type VARCHAR(50) NOT NULL, -- principle, motion, icp, signal, question, playbook, objection, battlecard, offer, guardrail, script, roleplay
    motion VARCHAR(50) NOT NULL DEFAULT 'cross_motion', -- growth, ai_automation, cross_motion
    stage VARCHAR(50) NOT NULL DEFAULT 'qualification', -- research, outreach, response, qualification, meeting, handoff, follow_up
    status VARCHAR(30) NOT NULL DEFAULT 'TESTING', -- HYPOTHESIS, TESTING, VALIDATED, DEPRECATED
    confidence NUMERIC(3, 2) NOT NULL DEFAULT 0.50,
    channels JSONB NOT NULL DEFAULT '["call", "whatsapp"]'::jsonb,
    audience JSONB NOT NULL DEFAULT '["sdr", "closer"]'::jsonb,
    aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    trigger TEXT,
    interpretation TEXT,
    objective TEXT,
    ask_first TEXT,
    call_talk_track TEXT,
    whatsapp_talk_track TEXT,
    email_talk_track TEXT,
    branches JSONB NOT NULL DEFAULT '[]'::jsonb,
    avoid JSONB NOT NULL DEFAULT '[]'::jsonb,
    next_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    version VARCHAR(20) NOT NULL DEFAULT '0.1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_cards_workspace ON sales_knowledge_cards(workspace_id);
CREATE INDEX IF NOT EXISTS idx_sales_cards_code ON sales_knowledge_cards(code);
CREATE INDEX IF NOT EXISTS idx_sales_cards_type ON sales_knowledge_cards(card_type);
CREATE INDEX IF NOT EXISTS idx_sales_cards_motion ON sales_knowledge_cards(motion);
CREATE INDEX IF NOT EXISTS idx_sales_cards_status ON sales_knowledge_cards(status);

-- 2. Listas de Prospecção (originadas do Radar Local de Mapas ou do CRM)
CREATE TABLE IF NOT EXISTS prospecting_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tenant_organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'local_radar', -- local_radar, crm, manual_import, csv
    segment VARCHAR(100),
    target_region VARCHAR(150),
    filters JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_leads INT NOT NULL DEFAULT 0,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prospecting_lists_workspace ON prospecting_lists(workspace_id);
CREATE INDEX IF NOT EXISTS idx_prospecting_lists_created ON prospecting_lists(created_at DESC);

-- 3. Itens / Leads da Lista de Prospecção (com suporte a Soft Warning de Deduplicação)
CREATE TABLE IF NOT EXISTS prospecting_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_id UUID NOT NULL REFERENCES prospecting_lists(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    website TEXT,
    instagram TEXT,
    linkedin TEXT,
    address TEXT,
    rating NUMERIC(3, 2),
    reviews_count INT NOT NULL DEFAULT 0,
    presence_score INT NOT NULL DEFAULT 0,
    category VARCHAR(100),
    external_place_id TEXT,
    crm_lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    ownership_warning JSONB DEFAULT NULL, -- Soft Warning se já abordado ou com outro responsável
    attempts_count INT NOT NULL DEFAULT 0,
    last_disposition VARCHAR(50), -- unanswered, busy, not_interested, wrong_person, follow_up, meeting_scheduled
    last_attempt_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL DEFAULT 'pending', -- pending, in_progress, completed, disqualified, archived
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prospecting_items_list ON prospecting_list_items(list_id);
CREATE INDEX IF NOT EXISTS idx_prospecting_items_status ON prospecting_list_items(status);
CREATE INDEX IF NOT EXISTS idx_prospecting_items_phone ON prospecting_list_items(phone);

-- 4. Sessões de Prospecção (Focus Mode / Bloco de Trabalho com Metas e Métricas)
CREATE TABLE IF NOT EXISTS prospecting_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    list_id UUID REFERENCES prospecting_lists(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    motion VARCHAR(50) NOT NULL DEFAULT 'growth',
    target_calls INT NOT NULL DEFAULT 30,
    completed_calls INT NOT NULL DEFAULT 0,
    connections_count INT NOT NULL DEFAULT 0,
    conversations_count INT NOT NULL DEFAULT 0,
    meetings_booked INT NOT NULL DEFAULT 0,
    follow_ups_count INT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_seconds INT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'active', -- active, paused, completed
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prospecting_sessions_workspace ON prospecting_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_prospecting_sessions_user ON prospecting_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_prospecting_sessions_status ON prospecting_sessions(status);

-- 5. Eventos e Disposições de Cada Ligação/Toque
CREATE TABLE IF NOT EXISTS prospecting_session_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES prospecting_sessions(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES prospecting_list_items(id) ON DELETE CASCADE,
    disposition VARCHAR(50) NOT NULL, -- unanswered, busy, wrong_number, not_interested, follow_up, meeting_scheduled
    notes TEXT,
    scheduled_follow_up_at TIMESTAMPTZ,
    handoff_payload JSONB DEFAULT NULL, -- Resumo estruturado para Closer / Sales Copilot
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_events_session ON prospecting_session_events(session_id);
CREATE INDEX IF NOT EXISTS idx_session_events_item ON prospecting_session_events(item_id);
