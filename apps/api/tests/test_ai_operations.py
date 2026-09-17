from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from bioma_api.services.ai_operations import (
    WORKFLOW_TEMPLATES,
    _eg_organization_id,
    _monthly_equivalent,
    _subscription_summary,
    list_templates,
)


def test_catalogo_tem_fluxos_prioritarios_e_etapas_unicas(eg_admin):
    templates = list_templates(eg_admin)

    assert {template.slug for template in templates} == {
        "commercial-proposal",
        "client-onboarding",
        "linkedin-content",
        "tech-delivery",
        "brand-book",
        "video-script",
    }
    for template in templates:
        keys = [step.key for step in template.steps]
        assert len(keys) == len(set(keys))
        assert any(step.interactive for step in template.steps)
        assert all(step.task_kind and step.capability for step in template.steps)


def test_template_onboarding_nao_depende_de_clickup():
    onboarding = WORKFLOW_TEMPLATES["client-onboarding"]

    assert onboarding["version"] == 3
    assert "Bioma" in onboarding["description"]
    assert all("clickup" not in step["key"].lower() for step in onboarding["steps"])


@pytest.mark.parametrize(
    ("amount_cents", "cycle", "months", "expected"),
    [
        (12000, "monthly", 1, 12000),
        (12000, "annual", 12, 1000),
        (1000, "custom", 3, 333),
        (1001, "custom", 2, 501),
    ],
)
def test_equivalencia_mensal_usa_centavos_sem_float(amount_cents, cycle, months, expected):
    assert _monthly_equivalent(amount_cents, cycle, months) == expected


def test_cota_restante_nunca_fica_negativa():
    summary = _subscription_summary(
        {
            "id": uuid4(),
            "provider": "provider",
            "product_name": "plan",
            "billing_mode": "subscription",
            "billing_cycle": "monthly",
            "billing_cycle_months": 1,
            "amount_cents": 100,
            "currency": "BRL",
            "seats": 1,
            "status": "active",
            "renews_at": None,
            "owner_label": None,
            "notes": None,
            "created_at": "2026-07-23T00:00:00Z",
            "updated_at": "2026-07-23T00:00:00Z",
            "quota_id": uuid4(),
            "total_units": Decimal("10"),
            "used_units": Decimal("12"),
            "quota_unit": "requests",
            "quota_source": "configured",
            "period_start": None,
            "period_end": None,
            "measured_at": "2026-07-23T00:00:00Z",
            "quota_notes": None,
        }
    )

    assert summary.latest_quota is not None
    assert summary.latest_quota.remaining_units == Decimal(0)


def test_finops_e_workflows_sao_exclusivos_do_admin_eg(client_user_factory):
    user = client_user_factory()

    with pytest.raises(HTTPException) as exc:
        _eg_organization_id(user)

    assert exc.value.status_code == 403
