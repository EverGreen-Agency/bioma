"""Catálogo server-owned do briefing comercial.

As chaves são persistidas na proposta; os rótulos podem evoluir sem quebrar
histórico nem depender de opções hardcoded apenas no frontend.
"""

PROPOSAL_TYPES = [
    {"key": "consulting", "label": "Consultoria"},
    {"key": "project", "label": "Projeto fechado"},
    {"key": "retainer", "label": "Contrato recorrente"},
    {"key": "implementation", "label": "Implementação"},
    {"key": "training", "label": "Treinamento"},
    {"key": "custom", "label": "Personalizada"},
]

DELIVERY_MODALITIES = [
    {"key": "project", "label": "Projeto com escopo fechado"},
    {"key": "monthly_retainer", "label": "Acompanhamento mensal"},
    {"key": "sprint", "label": "Sprint"},
    {"key": "hours_package", "label": "Banco de horas"},
    {"key": "hybrid", "label": "Modelo híbrido"},
]

URGENCY_LEVELS = [
    {"key": "low", "label": "Sem urgência definida"},
    {"key": "normal", "label": "Normal"},
    {"key": "high", "label": "Alta"},
    {"key": "critical", "label": "Crítica"},
]

SERVICE_GROUPS = [
    {
        "key": "marketing",
        "label": "Marketing e Growth",
        "services": [
            {"key": "paid_media", "label": "Tráfego pago"},
            {"key": "copywriting", "label": "Copywriting"},
            {"key": "web_landing_pages", "label": "Landing pages e websites"},
            {"key": "campaign_content_planning", "label": "Planejamento de campanhas e conteúdo"},
            {"key": "creative_design", "label": "Design e soluções criativas"},
            {"key": "seo_cro", "label": "SEO e CRO"},
            {"key": "email_automation", "label": "E-mail marketing e automações"},
            {"key": "analytics_bi", "label": "Dados, dashboards e relatórios"},
        ],
    },
    {
        "key": "commercial",
        "label": "Comercial",
        "services": [
            {"key": "sales_diagnosis", "label": "Diagnóstico do processo comercial"},
            {"key": "bdr_closer_structure", "label": "Estruturação de BDRs e Closers"},
            {"key": "sales_scripts", "label": "Scripts comerciais"},
            {"key": "sales_training", "label": "Treinamentos e reciclagens"},
            {"key": "sales_playbook", "label": "Implementação de playbook"},
            {"key": "goal_management", "label": "Acompanhamento e gestão de metas"},
            {"key": "sales_performance", "label": "Análise de performance"},
            {"key": "sales_simulations", "label": "Simulações de vendas"},
        ],
    },
    {
        "key": "implementation",
        "label": "Tecnologia e implementação",
        "services": [
            {"key": "crm_implementation", "label": "Implementação de CRM"},
            {"key": "sales_automation", "label": "Automações comerciais"},
            {"key": "advanced_tracking", "label": "Tracking avançado"},
            {"key": "voip_implementation", "label": "Implementação de VoIP"},
            {"key": "ai_service_agents", "label": "Agentes de IA para atendimento"},
            {"key": "software_development", "label": "Desenvolvimento de software"},
            {"key": "systems_integration", "label": "Integrações entre sistemas"},
        ],
    },
]

PROPOSAL_TYPE_KEYS = {item["key"] for item in PROPOSAL_TYPES}
DELIVERY_MODALITY_KEYS = {item["key"] for item in DELIVERY_MODALITIES}
URGENCY_KEYS = {item["key"] for item in URGENCY_LEVELS}
SERVICE_KEYS = {
    service["key"]
    for group in SERVICE_GROUPS
    for service in group["services"]
}


def proposal_catalog() -> dict:
    return {
        "schema_key": "commercial_proposal_v1",
        "schema_version": 1,
        "proposal_types": PROPOSAL_TYPES,
        "delivery_modalities": DELIVERY_MODALITIES,
        "urgency_levels": URGENCY_LEVELS,
        "service_groups": SERVICE_GROUPS,
    }
