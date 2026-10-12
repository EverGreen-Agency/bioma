from uuid import uuid4
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from bioma_api.schemas.ai_routing import (
    FreeProviderPresetRead,
    OrganizationBudgetRead,
    OrganizationBudgetUpdate,
    ProviderKeyPoolCreate,
    ProviderKeyPoolRead,
    UsageAnalyticsResponse,
)
from bioma_api.services.ai_routing import (
    list_free_providers,
    get_organization_budget,
    update_organization_budget,
)


def test_free_provider_preset_schema():
    preset = FreeProviderPresetRead(
        code="groq",
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        default_env_var="GROQ_API_KEY",
        description="Fast LPU",
        models=["llama-3.3-70b-versatile"],
        default_model="llama-3.3-70b-versatile",
        active_keys_count=2,
        has_env_key=True,
    )
    assert preset.code == "groq"
    assert preset.active_keys_count == 2
    assert preset.has_env_key is True


def test_provider_key_pool_create_validates_min_length():
    with pytest.raises(ValidationError):
        ProviderKeyPoolCreate(provider_code="", api_key="")


def test_organization_budget_schema_defaults():
    org_id = uuid4()
    budget = OrganizationBudgetRead(
        organization_id=org_id,
        monthly_token_cap=1_000_000,
        monthly_cost_cap_cents=5000,
        alert_threshold_percent=85,
        enforce_hard_stop=True,
        current_month_tokens=250_000,
        current_month_cost_cents=1200,
    )
    assert budget.organization_id == org_id
    assert budget.alert_threshold_percent == 85
    assert budget.enforce_hard_stop is True
    assert budget.current_month_tokens == 250_000


def test_usage_analytics_response_aggregation():
    res = UsageAnalyticsResponse(
        items=[
            {
                "date": "2026-09-18",
                "model": "llama-3.3-70b-versatile",
                "provider": "groq",
                "total_calls": 42,
                "total_tokens": 85000,
                "total_cost_cents": 0,
                "avg_latency_ms": 230,
            }
        ],
        total_tokens_month=85000,
        total_cost_cents_month=0,
        total_calls_month=42,
    )
    assert res.total_calls_month == 42
    assert res.items[0].avg_latency_ms == 230
