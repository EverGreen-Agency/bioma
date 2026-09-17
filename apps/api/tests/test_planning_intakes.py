import pytest
from fastapi import HTTPException

from contextlib import contextmanager
from uuid import uuid4

from bioma_api.planning_intakes import (
    COMMERCIAL_GOALS,
    MARKETING_GOALS,
    normalize_answers,
)
from bioma_api.schemas.projects import ProjectPlanningIntakeUpdate
from bioma_api.services import projects as project_service


def retail_answers():
    return {
        "product_categories": ["Roupas"],
        "upsell_cross_sell": "defined",
        "operating_channels": ["Loja física", "E-commerce"],
        "average_ticket_cents": 15000,
        "has_loyalty_program": False,
        "campaign_types": "Meta Ads e e-mail",
        "has_customer_system": True,
        "marketing_maturity": "advanced_automation",
        "marketing_goal": "predictive_marketing",
        "commercial_maturity": "advanced_automation",
        "commercial_goal": "sales_intelligence",
    }


def test_retail_intake_finalization_normalizes_and_derives_dynamic_options():
    answers, derived = normalize_answers("retail_v1", retail_answers(), require_complete=True)

    assert answers["product_categories"] == ["Roupas"]
    assert derived["marketing_goal_options"] == list(MARKETING_GOALS["advanced_automation"])
    assert derived["commercial_goal_options"] == list(COMMERCIAL_GOALS["advanced_automation"])


def test_retail_intake_rejects_goal_from_previous_maturity():
    answers = retail_answers()
    answers["marketing_maturity"] = "ad_hoc"

    with pytest.raises(HTTPException) as exc:
        normalize_answers("retail_v1", answers, require_complete=True)

    assert exc.value.status_code == 422
    assert "marketing_goal" in exc.value.detail


def test_retail_intake_requires_all_fields_only_when_finalized():
    answers, _ = normalize_answers("retail_v1", {"marketing_maturity": "none"}, require_complete=False)
    assert answers["marketing_maturity"] == "none"

    with pytest.raises(HTTPException) as exc:
        normalize_answers("retail_v1", {"marketing_maturity": "none"}, require_complete=True)

    assert exc.value.status_code == 422
    assert "operating_channels" in exc.value.detail


def test_tech_intake_normalizes_multi_value_fields():
    answers = {
        "product_stage": "evolution",
        "repository_strategy": "existing",
        "target_platforms": ["web", "mobile", "web"],
        "architecture_context": "React, FastAPI e PostgreSQL.",
        "environments": ["staging", "production"],
        "integrations": ["GitHub", "S3"],
        "data_strategy": "Migrações versionadas e rollback documentado.",
        "security_requirements": "Tenant scope e trilha de auditoria.",
        "acceptance_strategy": "Testes automatizados e aceite do cliente.",
        "release_goal": "Staging antes de produção.",
    }

    normalized, derived = normalize_answers("tech_v1", answers, require_complete=True)

    assert normalized["target_platforms"] == ["mobile", "web"]
    assert normalized["integrations"] == ["GitHub", "S3"]
    assert derived["schema_key"] == "tech_v1"
    assert "acceptance_strategy" in derived["answered_fields"]


def test_growth_social_intake_derives_adaptive_approval_flow():
    answers = {
        "channels": ["instagram", "linkedin"],
        "audience": "Decisores B2B e comunidade da marca.",
        "offer": "Estratégia, criação e distribuição de conteúdo.",
        "content_pillars": ["educação", "prova"],
        "cadence": "Três publicações por semana.",
        "approval_flow": "adaptive",
        "production_capacity": "Doze peças mensais.",
        "current_metrics": "Leads qualificados, alcance e salvamentos.",
        "campaign_goal": "Gerar demanda e fortalecer autoridade.",
        "brand_constraints": "Tom técnico, humano e sem promessas absolutas.",
    }

    normalized, derived = normalize_answers("growth_social_v1", answers, require_complete=True)

    assert normalized["channels"] == ["instagram", "linkedin"]
    assert derived["social_approval_flow"] == "adaptive"


def test_growth_social_intake_rejects_unknown_approval_flow():
    with pytest.raises(HTTPException) as exc:
        normalize_answers(
            "growth_social_v1",
            {"approval_flow": "automatic_without_review"},
            require_complete=False,
        )

    assert exc.value.status_code == 422
    assert "approval_flow" in exc.value.detail


def test_client_user_cannot_list_internal_planning_intakes(client_user_factory, monkeypatch):
    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(project_service, "connect", fake_connect)
    monkeypatch.setattr(
        project_service,
        "_project",
        lambda *_args, **_kwargs: {"access_role": "client_user", "id": uuid4()},
    )

    with pytest.raises(HTTPException) as exc:
        project_service.list_project_planning_intakes(uuid4(), client_user_factory())

    assert exc.value.status_code == 404


def test_finalized_intake_cannot_be_mutated(client_user_factory, monkeypatch):
    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(project_service, "connect", fake_connect)
    monkeypatch.setattr(
        project_service,
        "_planning_intake",
        lambda *_args, **_kwargs: {
            "id": uuid4(), "project_id": uuid4(), "organization_id": uuid4(),
            "status": "finalized", "schema_key": "retail_v1", "answers": retail_answers(),
        },
    )

    with pytest.raises(HTTPException) as exc:
        project_service.update_project_planning_intake(
            uuid4(), ProjectPlanningIntakeUpdate(title="Novo título"), client_user_factory(),
        )

    assert exc.value.status_code == 409
