import pytest
from pydantic import ValidationError

from bioma_api.schemas.ai_routing import (
    ProviderAccountCreate,
    ProviderAccountUpdate,
    QuotaBucketCreate,
    RoutingPolicyUpsert,
)


def test_antigravity_cli_aceita_executor_headless_oficial():
    account = ProviderAccountCreate(
        provider="google",
        channel="antigravity_cli",
        display_name="Assinatura Google",
        auth_mode="google_subscription",
        execution_mode="local_cli",
    )
    assert account.execution_mode == "local_cli"


def test_antigravity_cli_rejeita_modo_sdk():
    with pytest.raises(ValidationError):
        ProviderAccountCreate(
            provider="google",
            channel="antigravity_cli",
            display_name="Assinatura Google",
            auth_mode="google_subscription",
            execution_mode="sdk",
        )


def test_antigravity_sdk_usa_referencia_de_ambiente_sem_persistir_segredo():
    account = ProviderAccountCreate(
        provider="google",
        channel="antigravity_sdk",
        display_name="Gemini API",
        auth_mode="api_key",
        execution_mode="sdk",
        auth_ref="env:GEMINI_API_KEY",
    )
    assert account.auth_ref == "env:GEMINI_API_KEY"


def test_atualizacao_de_conta_tambem_rejeita_segredo_em_texto_puro():
    with pytest.raises(ValidationError):
        ProviderAccountUpdate(auth_ref="chave-em-texto-puro")


def test_cota_deriva_percentual_restante():
    bucket = QuotaBucketCreate(
        bucket_key="weekly",
        total_units=100,
        used_units=37,
        unit="requests",
        source="configured",
        confidence="manual",
    )
    assert bucket.used_percent == 37
    assert bucket.remaining_percent == 63


def test_pesos_da_politica_precisam_somar_cem():
    with pytest.raises(ValidationError):
        RoutingPolicyUpsert(
            task_kind="content_draft",
            capability="content",
            name="inválida",
            quality_weight=10,
        )
