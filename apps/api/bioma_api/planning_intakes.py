"""Versioned, server-owned planning-intake schemas and validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import HTTPException, status


RETAIL_SCHEMA_KEY = "retail_v1"
RETAIL_SCHEMA_VERSION = 1
TECH_SCHEMA_KEY = "tech_v1"
TECH_SCHEMA_VERSION = 1
GROWTH_SOCIAL_SCHEMA_KEY = "growth_social_v1"
GROWTH_SOCIAL_SCHEMA_VERSION = 1

MARKETING_GOALS = {
    "none": ("positioning_basics", "first_channels", "first_campaign", "other"),
    "ad_hoc": ("content_consistency", "campaign_calendar", "first_metrics", "other"),
    "recurring_unmeasured": ("measurement_foundation", "funnel_optimization", "content_performance", "other"),
    "measured_strategy": ("automation", "segmentation", "attribution", "other"),
    "advanced_automation": ("personalization_at_scale", "implement_ai_ml", "predictive_marketing", "advanced_omnichannel", "attribution_modeling", "other"),
}

COMMERCIAL_GOALS = {
    "unstructured": ("define_sales_process", "ideal_customer_profile", "basic_scripts", "other"),
    "relationship_led": ("pipeline_visibility", "sales_routine", "lead_qualification", "other"),
    "clear_pipeline": ("crm_implementation", "conversion_metrics", "sales_enablement", "other"),
    "measured_crm": ("sales_automation", "revenue_operations", "forecasting", "other"),
    "advanced_automation": ("sales_intelligence", "predictive_personalization", "nurturing_automation", "advanced_revops", "ai_sales_coaching", "other"),
}

RETAIL_MULTI_FIELDS = {"product_categories", "operating_channels"}
RETAIL_BOOLEAN_FIELDS = {"has_loyalty_program", "has_customer_system"}
RETAIL_REQUIRED_FIELDS = {
    "product_categories", "upsell_cross_sell", "operating_channels", "average_ticket_cents",
    "has_loyalty_program", "campaign_types", "has_customer_system",
    "marketing_maturity", "marketing_goal", "commercial_maturity", "commercial_goal",
}

TECH_FIELDS = (
    {"key": "product_stage", "label": "Estágio atual do produto", "type": "select", "options": ["discovery", "mvp", "evolution", "scale"]},
    {"key": "repository_strategy", "label": "Repositório e estratégia de branches", "type": "textarea"},
    {"key": "target_platforms", "label": "Plataformas-alvo", "type": "multi_text"},
    {"key": "architecture_context", "label": "Arquitetura e restrições atuais", "type": "textarea"},
    {"key": "environments", "label": "Ambientes", "type": "multi_text"},
    {"key": "integrations", "label": "Integrações e dependências", "type": "multi_text"},
    {"key": "data_strategy", "label": "Dados, migração e persistência", "type": "textarea"},
    {"key": "security_requirements", "label": "Segurança e compliance", "type": "textarea"},
    {"key": "acceptance_strategy", "label": "Testes e critérios de aceite", "type": "textarea"},
    {"key": "release_goal", "label": "Meta desta fase/release", "type": "textarea"},
)
TECH_REQUIRED_FIELDS = {field["key"] for field in TECH_FIELDS}
TECH_MULTI_FIELDS = {"target_platforms", "environments", "integrations"}

GROWTH_SOCIAL_FIELDS = (
    {"key": "channels", "label": "Canais prioritários", "type": "multi_text"},
    {"key": "audience", "label": "Público e momento de compra", "type": "textarea"},
    {"key": "offer", "label": "Oferta e objetivo de negócio", "type": "textarea"},
    {"key": "content_pillars", "label": "Pilares editoriais", "type": "multi_text"},
    {"key": "cadence", "label": "Cadência desejada", "type": "text"},
    {
        "key": "approval_flow",
        "label": "Fluxo de aprovação",
        "type": "select",
        "options": ["adaptive", "idea_before_production", "after_production", "final_only"],
    },
    {"key": "production_capacity", "label": "Capacidade e responsáveis", "type": "textarea"},
    {"key": "current_metrics", "label": "Baseline e métricas disponíveis", "type": "textarea"},
    {"key": "campaign_goal", "label": "Meta do ciclo", "type": "textarea"},
    {"key": "brand_constraints", "label": "Tom, restrições e referências", "type": "textarea"},
)
GROWTH_SOCIAL_REQUIRED_FIELDS = {field["key"] for field in GROWTH_SOCIAL_FIELDS}
GROWTH_SOCIAL_MULTI_FIELDS = {"channels", "content_pillars"}


def allowed_goals(kind: str, maturity: str) -> tuple[str, ...]:
    groups = MARKETING_GOALS if kind == "marketing" else COMMERCIAL_GOALS
    return groups.get(maturity, ())


def schema_version(schema_key: str) -> int:
    versions = {
        RETAIL_SCHEMA_KEY: RETAIL_SCHEMA_VERSION,
        TECH_SCHEMA_KEY: TECH_SCHEMA_VERSION,
        GROWTH_SOCIAL_SCHEMA_KEY: GROWTH_SOCIAL_SCHEMA_VERSION,
    }
    if schema_key not in versions:
        raise _unprocessable("Variante de planejamento não suportada.")
    return versions[schema_key]


def form_definition(schema_key: str) -> dict[str, Any]:
    if schema_key == RETAIL_SCHEMA_KEY:
        return {
            "schema_key": RETAIL_SCHEMA_KEY,
            "schema_version": RETAIL_SCHEMA_VERSION,
            "label": "Growth e operação comercial",
            "required_fields": sorted(RETAIL_REQUIRED_FIELDS),
            "fields": [],
            "marketing_maturities": list(MARKETING_GOALS),
            "commercial_maturities": list(COMMERCIAL_GOALS),
            "marketing_goals_by_maturity": {key: list(value) for key, value in MARKETING_GOALS.items()},
            "commercial_goals_by_maturity": {key: list(value) for key, value in COMMERCIAL_GOALS.items()},
        }
    if schema_key == TECH_SCHEMA_KEY:
        return {
            "schema_key": TECH_SCHEMA_KEY,
            "schema_version": TECH_SCHEMA_VERSION,
            "label": "Produto e engenharia",
            "required_fields": sorted(TECH_REQUIRED_FIELDS),
            "fields": list(TECH_FIELDS),
            "marketing_maturities": [],
            "commercial_maturities": [],
            "marketing_goals_by_maturity": {},
            "commercial_goals_by_maturity": {},
        }
    if schema_key == GROWTH_SOCIAL_SCHEMA_KEY:
        return {
            "schema_key": GROWTH_SOCIAL_SCHEMA_KEY,
            "schema_version": GROWTH_SOCIAL_SCHEMA_VERSION,
            "label": "Growth e social media",
            "required_fields": sorted(GROWTH_SOCIAL_REQUIRED_FIELDS),
            "fields": list(GROWTH_SOCIAL_FIELDS),
            "marketing_maturities": [],
            "commercial_maturities": [],
            "marketing_goals_by_maturity": {},
            "commercial_goals_by_maturity": {},
        }
    raise _unprocessable("Variante de planejamento não suportada.")


def normalize_answers(
    schema_key: str,
    answers: dict[str, Any],
    *,
    require_complete: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(answers, dict):
        raise _unprocessable("As respostas da intake precisam ser um objeto.")
    if schema_key == RETAIL_SCHEMA_KEY:
        return _normalize_retail(answers, require_complete=require_complete)
    if schema_key == TECH_SCHEMA_KEY:
        return _normalize_generic(
            schema_key,
            answers,
            required=TECH_REQUIRED_FIELDS,
            multi=TECH_MULTI_FIELDS,
            require_complete=require_complete,
        )
    if schema_key == GROWTH_SOCIAL_SCHEMA_KEY:
        normalized, derived = _normalize_generic(
            schema_key,
            answers,
            required=GROWTH_SOCIAL_REQUIRED_FIELDS,
            multi=GROWTH_SOCIAL_MULTI_FIELDS,
            require_complete=require_complete,
        )
        allowed_flows = {"adaptive", "idea_before_production", "after_production", "final_only"}
        if normalized.get("approval_flow") is not None and normalized["approval_flow"] not in allowed_flows:
            raise _unprocessable("approval_flow não é uma opção válida.")
        derived["social_approval_flow"] = normalized.get("approval_flow", "adaptive")
        return normalized, derived
    raise _unprocessable("Variante de planejamento não suportada.")


def _normalize_retail(answers: dict[str, Any], *, require_complete: bool):
    normalized = deepcopy(answers)
    _normalize_multi_fields(normalized, RETAIL_MULTI_FIELDS)
    for field in RETAIL_BOOLEAN_FIELDS:
        if field in normalized and not isinstance(normalized[field], bool):
            raise _unprocessable(f"{field} precisa ser verdadeiro ou falso.")
    if normalized.get("average_ticket_cents") is not None and (
        not isinstance(normalized["average_ticket_cents"], int) or normalized["average_ticket_cents"] < 0
    ):
        raise _unprocessable("average_ticket_cents precisa ser um inteiro não negativo.")
    for field in ("upsell_cross_sell", "campaign_types"):
        if field in normalized and (not isinstance(normalized[field], str) or not normalized[field].strip()):
            raise _unprocessable(f"{field} precisa ser preenchido.")
    for kind, maturity_field, goal_field in (
        ("marketing", "marketing_maturity", "marketing_goal"),
        ("commercial", "commercial_maturity", "commercial_goal"),
    ):
        maturity = normalized.get(maturity_field)
        goal = normalized.get(goal_field)
        groups = MARKETING_GOALS if kind == "marketing" else COMMERCIAL_GOALS
        if maturity is not None and maturity not in groups:
            raise _unprocessable(f"{maturity_field} não é uma opção válida.")
        if goal is not None and goal not in allowed_goals(kind, maturity):
            raise _unprocessable(f"{goal_field} não é compatível com a maturidade selecionada.")
    _require_fields(normalized, RETAIL_REQUIRED_FIELDS, require_complete)
    return normalized, {
        "schema_key": RETAIL_SCHEMA_KEY,
        "schema_version": RETAIL_SCHEMA_VERSION,
        "marketing_goal_options": list(allowed_goals("marketing", normalized.get("marketing_maturity", ""))),
        "commercial_goal_options": list(allowed_goals("commercial", normalized.get("commercial_maturity", ""))),
    }


def _normalize_generic(
    schema_key: str,
    answers: dict[str, Any],
    *,
    required: set[str],
    multi: set[str],
    require_complete: bool,
):
    normalized = deepcopy(answers)
    unknown = sorted(set(normalized) - required)
    if unknown:
        raise _unprocessable("Campos não suportados nesta variante: " + ", ".join(unknown) + ".")
    _normalize_multi_fields(normalized, multi)
    for field, value in normalized.items():
        if field not in multi and value is not None and (not isinstance(value, str) or not value.strip()):
            raise _unprocessable(f"{field} precisa ser um texto válido.")
        if isinstance(value, str):
            normalized[field] = value.strip()
    _require_fields(normalized, required, require_complete)
    return normalized, {
        "schema_key": schema_key,
        "schema_version": schema_version(schema_key),
        "answered_fields": sorted(key for key, value in normalized.items() if value not in (None, "", [])),
    }


def _normalize_multi_fields(normalized: dict[str, Any], fields: set[str]) -> None:
    for field in fields:
        if field in normalized and normalized[field] is not None:
            if not isinstance(normalized[field], list) or not all(
                isinstance(value, str) and value.strip() for value in normalized[field]
            ):
                raise _unprocessable(f"{field} precisa ser uma lista de opções válidas.")
            normalized[field] = sorted(set(value.strip() for value in normalized[field]))


def _require_fields(normalized: dict[str, Any], required: set[str], require_complete: bool) -> None:
    if not require_complete:
        return
    missing = sorted(field for field in required if normalized.get(field) in (None, "", []))
    if missing:
        raise _unprocessable("Finalize os campos obrigatórios: " + ", ".join(missing) + ".")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
