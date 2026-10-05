from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.crypto import encrypt_secret, require_encryption_configured
from bioma_api import provider_login
from bioma_api.repositories import ai_routing as repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.schemas.ai_routing import (
    AiRoutingControlPlane,
    FreeProviderPresetRead,
    HarnessConfigSummary,
    HarnessConfigUpsert,
    ModelCatalogSummary,
    ModelCatalogUpsert,
    OrganizationBudgetRead,
    OrganizationBudgetUpdate,
    ProviderAccountCreate,
    ProviderAccountSummary,
    ProviderAccountUpdate,
    ProviderKeyPoolCreate,
    ProviderKeyPoolRead,
    ProviderLoginInput,
    ProviderLoginSession,
    ProviderRuntimeStatus,
    QuotaBucketCreate,
    QuotaBucketSummary,
    QuotaCollectionJobSummary,
    RouteCandidate,
    RoutePreview,
    RoutePreviewRequest,
    RoutingPolicySummary,
    RoutingPolicyUpsert,
    UsageAnalyticsItem,
    UsageAnalyticsResponse,
)
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services.ai_operations import _eg_organization_id
from bioma_api.config import get_settings
from bioma_api.worker_bridge import (
    ai_provider_settings_safe,
    probe_ai_provider_runtime_safe,
    purge_provider_credentials_safe,
)
from bioma_worker.free_providers import (
    FREE_PROVIDER_PRESETS,
    make_key_fingerprint,
    execute_free_provider_call,
)


MODEL_PRESETS: dict[str, list[dict[str, Any]]] = {
    "codex_chatgpt": [
        {
            "model_id": "gpt-5.6-luna",
            "display_name": "GPT-5.6 Luna",
            "family": "gpt-5.6",
            "capability_tier": "economy",
            "capabilities": ["chat", "content", "code", "reasoning", "structured_output"],
            "quality_score": 74,
            "cost_score": 95,
            "latency_score": 92,
            "priority": 30,
        },
        {
            "model_id": "gpt-5.6-terra",
            "display_name": "GPT-5.6 Terra",
            "family": "gpt-5.6",
            "capability_tier": "balanced",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools", "structured_output"],
            "quality_score": 88,
            "cost_score": 75,
            "latency_score": 78,
            "priority": 20,
        },
        {
            "model_id": "gpt-5.6-sol",
            "display_name": "GPT-5.6 Sol",
            "family": "gpt-5.6",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools", "structured_output"],
            "quality_score": 98,
            "cost_score": 45,
            "latency_score": 55,
            "priority": 10,
        },
    ],
    "claude_code": [
        {
            "model_id": "haiku",
            "display_name": "Claude Haiku (alias da conta)",
            "family": "claude",
            "capability_tier": "economy",
            "capabilities": ["chat", "content", "code", "reasoning", "structured_output"],
            "quality_score": 72,
            "cost_score": 96,
            "latency_score": 96,
            "priority": 30,
        },
        {
            "model_id": "sonnet",
            "display_name": "Claude Sonnet (alias da conta)",
            "family": "claude",
            "capability_tier": "balanced",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools", "structured_output"],
            "quality_score": 90,
            "cost_score": 72,
            "latency_score": 80,
            "priority": 20,
        },
        {
            "model_id": "opus",
            "display_name": "Claude Opus (alias da conta)",
            "family": "claude",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools", "structured_output"],
            "quality_score": 98,
            "cost_score": 35,
            "latency_score": 50,
            "priority": 10,
        },
    ],
    "antigravity_cli": [
        {
            "model_id": "gemini-3.7-flash-medium",
            "display_name": "Gemini 3.7 Flash (Medium)",
            "family": "gemini",
            "capability_tier": "economy",
            "capabilities": ["chat", "content", "code", "reasoning", "tools", "multimodal"],
            "quality_score": 82,
            "cost_score": 92,
            "latency_score": 94,
            "priority": 30,
        },
        {
            "model_id": "gemini-3.1-pro-high",
            "display_name": "Gemini 3.1 Pro (High)",
            "family": "gemini",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools", "multimodal"],
            "quality_score": 96,
            "cost_score": 48,
            "latency_score": 58,
            "priority": 10,
        },
        {
            "model_id": "claude-sonnet-4-6",
            "display_name": "Claude Sonnet 4.6 (Thinking)",
            "family": "claude",
            "capability_tier": "balanced",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools"],
            "quality_score": 92,
            "cost_score": 65,
            "latency_score": 70,
            "priority": 20,
        },
        {
            "model_id": "claude-opus-4-6",
            "display_name": "Claude Opus 4.6 (Thinking)",
            "family": "claude",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools"],
            "quality_score": 99,
            "cost_score": 30,
            "latency_score": 45,
            "priority": 15,
        },
        {
            "model_id": "gpt-oss-120b",
            "display_name": "GPT-OSS 120B",
            "family": "gpt-oss",
            "capability_tier": "specialist",
            "capabilities": ["chat", "content", "code", "reasoning"],
            "quality_score": 78,
            "cost_score": 80,
            "latency_score": 70,
            "priority": 40,
        },
    ],
    "antigravity_sdk": [
        {
            "model_id": "gemini-3.6-flash",
            "display_name": "Gemini 3.6 Flash",
            "family": "gemini",
            "capability_tier": "economy",
            "capabilities": ["chat", "content", "code", "reasoning", "tools", "multimodal", "structured_output"],
            "quality_score": 82,
            "cost_score": 92,
            "latency_score": 94,
            "priority": 20,
        },
        {
            "model_id": "gemini-3.1-pro",
            "display_name": "Gemini 3.1 Pro",
            "family": "gemini",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools", "multimodal", "structured_output"],
            "quality_score": 96,
            "cost_score": 48,
            "latency_score": 58,
            "priority": 10,
        },
    ],
    "openrouter": [
        {
            "model_id": "openrouter/auto",
            "display_name": "OpenRouter Auto Router",
            "family": "openrouter",
            "capability_tier": "balanced",
            "capabilities": ["chat", "content", "code", "reasoning", "tools"],
            "quality_score": 85,
            "cost_score": 85,
            "latency_score": 85,
            "priority": 10,
        },
        {
            "model_id": "anthropic/claude-sonnet-4.6",
            "display_name": "Claude Sonnet 4.6 (OpenRouter)",
            "family": "claude",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "reasoning", "tools"],
            "quality_score": 95,
            "cost_score": 70,
            "latency_score": 75,
            "priority": 20,
        },
        {
            "model_id": "deepseek/deepseek-r1",
            "display_name": "DeepSeek R1 (OpenRouter)",
            "family": "deepseek",
            "capability_tier": "frontier",
            "capabilities": ["reasoning", "code", "strategy", "tools"],
            "quality_score": 97,
            "cost_score": 90,
            "latency_score": 60,
            "priority": 15,
        },
    ],
    "deepseek": [
        {
            "model_id": "deepseek-v4-pro",
            "display_name": "DeepSeek V4 Pro",
            "family": "deepseek",
            "capability_tier": "frontier",
            "capabilities": ["reasoning", "strategy", "code"],
            "quality_score": 98,
            "cost_score": 92,
            "latency_score": 60,
            "priority": 10,
        },
        {
            "model_id": "deepseek-v4-flash",
            "display_name": "DeepSeek V4 Flash",
            "family": "deepseek",
            "capability_tier": "balanced",
            "capabilities": ["chat", "content", "code", "tools"],
            "quality_score": 90,
            "cost_score": 95,
            "latency_score": 85,
            "priority": 20,
        },
    ],
}
MODEL_PRESETS["gemini_api"] = MODEL_PRESETS["antigravity_sdk"]
MODEL_PRESETS["vertex"] = MODEL_PRESETS["antigravity_sdk"]


DEFAULT_POLICIES = [
    RoutingPolicyUpsert(
        task_kind="reasoning",
        capability="reasoning",
        name="Planejador do copiloto",
        preferred_tiers=["balanced", "frontier"],
        quality_weight=50,
        quota_weight=20,
        cost_weight=10,
        reliability_weight=15,
        latency_weight=5,
        minimum_quota_headroom=15,
    ),
    RoutingPolicyUpsert(
        task_kind="tool_calling",
        capability="tools",
        name="Executor de ferramentas",
        preferred_tiers=["balanced"],
        quality_weight=35,
        quota_weight=20,
        cost_weight=15,
        reliability_weight=20,
        latency_weight=10,
        minimum_quota_headroom=15,
    ),
    RoutingPolicyUpsert(
        task_kind="quality_audit",
        capability="reasoning",
        name="Auditor de qualidade",
        preferred_tiers=["frontier"],
        quality_weight=60,
        quota_weight=10,
        cost_weight=5,
        reliability_weight=20,
        latency_weight=5,
        minimum_quota_headroom=20,
    ),
    RoutingPolicyUpsert(
        task_kind="knowledge_curation",
        capability="structured_output",
        name="Curador de conhecimento",
        preferred_tiers=["balanced", "frontier"],
        quality_weight=45,
        quota_weight=15,
        cost_weight=15,
        reliability_weight=20,
        latency_weight=5,
        minimum_quota_headroom=15,
    ),
    RoutingPolicyUpsert(
        task_kind="internal_chat",
        capability="chat",
        name="Chat interno econômico",
        preferred_tiers=["economy", "balanced"],
        quality_weight=25,
        quota_weight=25,
        cost_weight=25,
        reliability_weight=10,
        latency_weight=15,
        minimum_quota_headroom=10,
    ),
    RoutingPolicyUpsert(
        task_kind="content_draft",
        capability="content",
        name="Rascunho de conteúdo",
        preferred_tiers=["balanced"],
        quality_weight=40,
        quota_weight=20,
        cost_weight=20,
        reliability_weight=10,
        latency_weight=10,
        minimum_quota_headroom=15,
    ),
    RoutingPolicyUpsert(
        task_kind="brand_strategy",
        capability="strategy",
        name="Estratégia e brand book",
        preferred_tiers=["frontier"],
        quality_weight=60,
        quota_weight=15,
        cost_weight=5,
        reliability_weight=15,
        latency_weight=5,
        minimum_quota_headroom=20,
    ),
    RoutingPolicyUpsert(
        task_kind="code_agent",
        capability="code",
        name="Execução de engenharia e squads",
        allowed_channels=["codex_chatgpt", "claude_code", "antigravity_sdk", "gemini_api", "vertex"],
        preferred_tiers=["balanced", "frontier"],
        quality_weight=45,
        quota_weight=20,
        cost_weight=10,
        reliability_weight=15,
        latency_weight=10,
        minimum_quota_headroom=15,
    ),
]


def _control_plane(organization_id: UUID) -> AiRoutingControlPlane:
    with connect() as conn:
        account_rows = repo.list_accounts(conn, organization_id)
        model_rows = repo.list_models(conn, organization_id)
        quota_rows = repo.list_latest_quota_buckets(conn, organization_id)
        policy_rows = repo.list_policies(conn, organization_id)
        quota_job_rows = repo.list_quota_collection_jobs(conn, organization_id)
        harness_row = repo.get_harness_config(conn, organization_id)
    models_by_account: dict[UUID, list[ModelCatalogSummary]] = defaultdict(list)
    quotas_by_account: dict[UUID, list[QuotaBucketSummary]] = defaultdict(list)
    for row in model_rows:
        models_by_account[row["account_id"]].append(ModelCatalogSummary(**row))
    for row in quota_rows:
        account_id = row["account_id"]
        quota_data = {key: value for key, value in row.items() if key != "account_id"}
        quotas_by_account[account_id].append(QuotaBucketSummary(**quota_data))
    accounts = [
        ProviderAccountSummary(
            **row,
            models=models_by_account[row["id"]],
            quota_buckets=quotas_by_account[row["id"]],
        )
        for row in account_rows
    ]
    return AiRoutingControlPlane(
        accounts=accounts,
        policies=[RoutingPolicySummary(**row) for row in policy_rows],
        harness_config=HarnessConfigSummary(**harness_row) if harness_row else None,
        quota_collection_jobs=[QuotaCollectionJobSummary(**row) for row in quota_job_rows],
        generated_at=datetime.now(timezone.utc),
    )


def get_control_plane(user: CurrentUserResponse) -> AiRoutingControlPlane:
    return _control_plane(_eg_organization_id(user))


def create_account(payload: ProviderAccountCreate, user: CurrentUserResponse) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        row = repo.create_account(conn, organization_id, user.id, payload.model_dump())
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.provider_account.created",
            {
                "account_id": str(row["id"]),
                "provider": payload.provider,
                "channel": payload.channel,
                "execution_mode": payload.execution_mode,
            },
        )
    return _control_plane(organization_id)


def update_account(
    account_id: UUID,
    payload: ProviderAccountUpdate,
    user: CurrentUserResponse,
) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        if not repo.update_account(conn, organization_id, account_id, user.id, updates):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.provider_account.updated",
            {"account_id": str(account_id), "fields": sorted(updates)},
        )
    return _control_plane(organization_id)


def upsert_model(
    account_id: UUID,
    payload: ModelCatalogUpsert,
    user: CurrentUserResponse,
) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        row = repo.upsert_model(conn, organization_id, account_id, payload.model_dump())
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.model.upserted",
            {"account_id": str(account_id), "model_id": payload.model_id},
        )
    return _control_plane(organization_id)


def bootstrap_models(account_id: UUID, user: CurrentUserResponse) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    control = _control_plane(organization_id)
    account = next((item for item in control.accounts if item.id == account_id), None)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
    presets = MODEL_PRESETS.get(account.channel)
    if not presets:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Canal {account.channel} não possui catálogo inicial. Cadastre os modelos explicitamente.",
        )
    with connect() as conn:
        for preset in presets:
            data = ModelCatalogUpsert(**preset).model_dump()
            repo.upsert_model(conn, organization_id, account_id, data)
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.model_catalog.bootstrapped",
            {"account_id": str(account_id), "channel": account.channel, "models": len(presets)},
        )
    return _control_plane(organization_id)


def record_quota(
    account_id: UUID,
    payload: QuotaBucketCreate,
    user: CurrentUserResponse,
) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    data = payload.model_dump()
    with connect() as conn:
        row = repo.create_quota_bucket(conn, organization_id, account_id, user.id, data)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.quota_bucket.recorded",
            {
                "account_id": str(account_id),
                "quota_bucket_id": str(row["id"]),
                "bucket_key": payload.bucket_key,
                "source": payload.source,
                "confidence": payload.confidence,
            },
        )
    return _control_plane(organization_id)


def enqueue_quota_collection(account_id: UUID, user: CurrentUserResponse) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        row = repo.enqueue_quota_collection(conn, organization_id, account_id, user.id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Coleta automática está disponível para Codex, Claude Code e Antigravity CLI."
                ),
            )
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.quota_collection.queued",
            {"account_id": str(account_id), "job_id": str(row["id"])},
        )
    return _control_plane(organization_id)


def probe_runtime(account_id: UUID, user: CurrentUserResponse) -> ProviderRuntimeStatus:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        account = repo.get_account(conn, account_id)
    if not account or account["organization_id"] != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
    result = probe_ai_provider_runtime_safe(dict(account))
    with connect() as conn:
        repo.record_runtime_probe(conn, organization_id, account_id, result)
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.provider_runtime.probed",
            {"account_id": str(account_id), "ready": result["ready"], "channel": result["channel"]},
        )
    return ProviderRuntimeStatus(**result)


def start_provider_login(account_id: UUID, user: CurrentUserResponse) -> ProviderLoginSession:
    require_platform_admin(user)
    require_encryption_configured()
    runtime_settings = ai_provider_settings_safe()
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        account = repo.get_account(conn, account_id)
        if not account or account["organization_id"] != organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
        if account["channel"] not in {"codex_chatgpt", "claude_code", "antigravity_cli"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Este canal usa chave/ADC e não possui login interativo por assinatura.",
            )
        row, canceled_session_ids = repo.create_login_session(conn, organization_id, account_id, user.id)
        if not row:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Canal não elegível para login.")
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.provider_account.login_started",
            {"account_id": str(account_id), "channel": account["channel"], "session_id": str(row["id"])},
        )
    for canceled_session_id in canceled_session_ids:
        provider_login.stop_login(canceled_session_id)
    provider_login.start_login(row["id"], dict(account), user.id, runtime_settings)
    return get_provider_login(row["id"], user)


def get_provider_login(session_id: UUID, user: CurrentUserResponse) -> ProviderLoginSession:
    require_platform_admin(user)
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        row = repo.get_login_session(conn, organization_id, session_id)
        now = datetime.now(timezone.utc)
        active = row and row["status"] in {"pending", "running", "waiting_input"}
        if active and row["expires_at"] <= now:
            conn.execute(
                """update ai_provider_login_sessions set status = 'expired',
                error_message = 'O login expirou após 15 minutos.', finished_at = now(), updated_at = now()
                where id = %s""",
                (session_id,),
            )
            row = repo.get_login_session(conn, organization_id, session_id)
        elif (
            active
            and row["started_at"] is not None
            and row["updated_at"] <= now - timedelta(seconds=provider_login.LOGIN_STALE_SECONDS)
        ):
            conn.execute(
                """update ai_provider_login_sessions set status = 'failed',
                encrypted_pending_input = null,
                error_message = 'O processo de login foi interrompido. Inicie uma nova tentativa.',
                finished_at = now(), updated_at = now()
                where id = %s and status in ('pending', 'running', 'waiting_input')""",
                (session_id,),
            )
            row = repo.get_login_session(conn, organization_id, session_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão de login não encontrada.")
    return ProviderLoginSession(**row)


def send_provider_login_input(
    session_id: UUID, payload: ProviderLoginInput, user: CurrentUserResponse
) -> ProviderLoginSession:
    require_platform_admin(user)
    require_encryption_configured()
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        if not repo.queue_login_input(conn, organization_id, session_id, encrypt_secret(payload.value)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sessão encerrada, expirada ou não encontrada.",
            )
    return get_provider_login(session_id, user)


def cancel_provider_login(session_id: UUID, user: CurrentUserResponse) -> ProviderLoginSession:
    require_platform_admin(user)
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        if not repo.cancel_login_session(conn, organization_id, session_id):
            existing = repo.get_login_session(conn, organization_id, session_id)
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão de login não encontrada.")
        else:
            client_hub_repo.write_audit(
                conn, user.id, organization_id, "ai.provider_account.login_canceled",
                {"session_id": str(session_id)},
            )
    provider_login.stop_login(session_id)
    return get_provider_login(session_id, user)


def disconnect_provider_credentials(account_id: UUID, user: CurrentUserResponse) -> AiRoutingControlPlane:
    """Remove a sessão do Bioma; revogação no provedor continua sendo externa."""
    require_platform_admin(user)
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        account = repo.get_account(conn, account_id)
        if not account or account["organization_id"] != organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
        if account["channel"] not in {"codex_chatgpt", "claude_code", "antigravity_cli"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Este canal usa chave/ADC e não possui credencial de assinatura no cofre.",
            )
        if not repo.disconnect_provider_credentials(conn, organization_id, account_id, user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.provider_account.disconnected",
            {
                "account_id": str(account_id),
                "channel": account["channel"],
                "credential_was_configured": bool(account.get("credential_bundle")),
                "upstream_revocation_required": True,
            },
        )
    purge_provider_credentials_safe(account_id)
    return _control_plane(organization_id)


def upsert_policy(payload: RoutingPolicyUpsert, user: CurrentUserResponse) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        row = repo.upsert_policy(conn, organization_id, user.id, payload.model_dump())
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.routing_policy.upserted",
            {"policy_id": str(row["id"]), "task_kind": payload.task_kind},
        )
    return _control_plane(organization_id)


def bootstrap_policies(user: CurrentUserResponse) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        for policy in DEFAULT_POLICIES:
            repo.upsert_policy(conn, organization_id, user.id, policy.model_dump())
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.routing_policies.bootstrapped",
            {"policies": [policy.task_kind for policy in DEFAULT_POLICIES]},
        )
    return _control_plane(organization_id)


def upsert_harness(payload: HarnessConfigUpsert, user: CurrentUserResponse) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        row = repo.upsert_harness_config(conn, organization_id, user.id, payload.model_dump())
        if not row:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Um dos modelos do Harness não pertence ao catálogo desta organização.",
            )
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.harness.updated",
            {"roles": [key for key, value in payload.model_dump().items() if key.endswith("_model_catalog_id") and value]},
        )
    return _control_plane(organization_id)


def _quota_headroom(account: ProviderAccountSummary) -> Decimal | None:
    now = datetime.now(timezone.utc)
    current = [
        bucket.remaining_percent
        for bucket in account.quota_buckets
        if bucket.remaining_percent is not None
        and (bucket.resets_at is None or bucket.resets_at > now)
        and bucket.confidence != "unavailable"
    ]
    return min(current) if current else None


def preview_route(payload: RoutePreviewRequest, user: CurrentUserResponse) -> RoutePreview:
    organization_id = _eg_organization_id(user)
    control = _control_plane(organization_id)
    policy = next(
        (item for item in control.policies if item.task_kind == payload.task_kind and item.status == "active"),
        None,
    )
    capability = payload.capability or (policy.capability if policy else payload.task_kind)
    candidates: list[RouteCandidate] = []
    for account in control.accounts:
        reliability = 100 if account.status == "active" else 40 if account.status == "degraded" else 0
        headroom = _quota_headroom(account)
        for model in account.models:
            reasons: list[str] = []
            eligible = account.status in ("active", "degraded") and model.enabled
            if account.channel in {"codex_chatgpt", "claude_code", "antigravity_cli"} and not account.credentials_configured:
                eligible = False
                reasons.append("assinatura ainda não conectada ao cofre do Bioma")
            if account.execution_mode == "manual_handoff":
                eligible = False
                reasons.append("canal exige handoff manual")
            capabilities = set(account.capabilities) | set(model.capabilities)
            if capability not in capabilities:
                eligible = False
                reasons.append(f"capacidade ausente: {capability}")
            if policy and policy.allowed_channels and account.channel not in policy.allowed_channels:
                eligible = False
                reasons.append("canal não permitido pela política")
            if policy and policy.allowed_models and model.model_id not in policy.allowed_models:
                eligible = False
                reasons.append("modelo não permitido pela política")
            minimum = policy.minimum_quota_headroom if policy else Decimal(10)
            if headroom is not None and headroom < minimum:
                eligible = False
                reasons.append(f"cota abaixo da reserva ({headroom}% < {minimum}%)")
            if headroom is None:
                reasons.append("cota externa sem medição atual; decisão não é garantida")
            else:
                reasons.append(f"folga de cota: {headroom}%")
            if policy and policy.preferred_tiers and model.capability_tier in policy.preferred_tiers:
                reasons.append(f"tier preferido: {model.capability_tier}")
            weights = policy or DEFAULT_POLICIES[0]
            quota_score = headroom if headroom is not None else Decimal(50)
            score = (
                Decimal(model.quality_score * weights.quality_weight)
                + quota_score * Decimal(weights.quota_weight)
                + Decimal(model.cost_score * weights.cost_weight)
                + Decimal(reliability * weights.reliability_weight)
                + Decimal(model.latency_score * weights.latency_weight)
            ) / Decimal(100)
            if policy and policy.preferred_tiers and model.capability_tier not in policy.preferred_tiers:
                score -= Decimal(8)
            candidates.append(
                RouteCandidate(
                    account_id=account.id,
                    model_catalog_id=model.id,
                    provider=account.provider,
                    channel=account.channel,
                    model_id=model.model_id,
                    display_name=model.display_name,
                    score=max(score, Decimal(0)).quantize(Decimal("0.01")),
                    quota_headroom=headroom,
                    eligible=eligible,
                    reasons=reasons,
                )
            )
    candidates.sort(key=lambda item: (item.eligible, item.score), reverse=True)
    selected = next((candidate for candidate in candidates if candidate.eligible), None)
    return RoutePreview(
        task_kind=payload.task_kind,
        policy_id=policy.id if policy else None,
        selected=selected,
        candidates=candidates,
    )


def list_free_providers(user: CurrentUserResponse) -> list[FreeProviderPresetRead]:
    require_platform_admin(user)
    key_counts: dict[str, int] = {}
    with connect() as conn:
        try:
            rows = conn.execute(
                """
                SELECT provider_code, COUNT(*) as count
                FROM ai_provider_key_pool
                WHERE status = 'active'
                GROUP BY provider_code
                """
            ).fetchall()
            for r in rows:
                key_counts[r["provider_code"]] = int(r["count"])
        except Exception:
            pass

    import os
    result: list[FreeProviderPresetRead] = []
    for code, preset in FREE_PROVIDER_PRESETS.items():
        env_var = preset.get("default_env_var", "")
        has_env = bool(os.environ.get(env_var)) if env_var else False
        result.append(
            FreeProviderPresetRead(
                code=code,
                name=preset["name"],
                base_url=preset["base_url"],
                default_env_var=env_var,
                description=preset["description"],
                models=preset["models"],
                default_model=preset["default_model"],
                active_keys_count=key_counts.get(code, 0),
                has_env_key=has_env,
            )
        )
    return result


def list_provider_keys(provider_code: str | None, user: CurrentUserResponse) -> list[ProviderKeyPoolRead]:
    require_platform_admin(user)
    with connect() as conn:
        try:
            if provider_code:
                rows = conn.execute(
                    """
                    SELECT id, provider_code, label, key_fingerprint, status,
                           error_count, call_count, last_used_at, cooldown_until,
                           last_error_message, created_at
                    FROM ai_provider_key_pool
                    WHERE provider_code = %s
                    ORDER BY created_at DESC
                    """,
                    (provider_code,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, provider_code, label, key_fingerprint, status,
                           error_count, call_count, last_used_at, cooldown_until,
                           last_error_message, created_at
                    FROM ai_provider_key_pool
                    ORDER BY created_at DESC
                    """
                ).fetchall()
            return [
                ProviderKeyPoolRead(
                    id=r["id"],
                    provider_code=r["provider_code"],
                    label=r["label"],
                    key_fingerprint=r["key_fingerprint"],
                    status=r["status"],
                    error_count=r["error_count"],
                    call_count=r["call_count"],
                    last_used_at=r["last_used_at"],
                    cooldown_until=r["cooldown_until"],
                    last_error_message=r["last_error_message"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        except Exception:
            return []


def create_provider_key(payload: ProviderKeyPoolCreate, user: CurrentUserResponse) -> ProviderKeyPoolRead:
    require_platform_admin(user)
    require_encryption_configured()
    settings = get_settings()

    encrypted = encrypt_secret(payload.api_key.strip(), settings.secret_encryption_key)
    fingerprint = make_key_fingerprint(payload.api_key)

    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO ai_provider_key_pool (
                provider_code, label, key_encrypted, key_fingerprint, status, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 'active', now(), now())
            RETURNING id, provider_code, label, key_fingerprint, status,
                      error_count, call_count, last_used_at, cooldown_until,
                      last_error_message, created_at
            """,
            (payload.provider_code, payload.label, encrypted, fingerprint),
        ).fetchone()

        return ProviderKeyPoolRead(
            id=row["id"],
            provider_code=row["provider_code"],
            label=row["label"],
            key_fingerprint=row["key_fingerprint"],
            status=row["status"],
            error_count=row["error_count"],
            call_count=row["call_count"],
            last_used_at=row["last_used_at"],
            cooldown_until=row["cooldown_until"],
            last_error_message=row["last_error_message"],
            created_at=row["created_at"],
        )


def delete_provider_key(key_id: UUID, user: CurrentUserResponse) -> None:
    require_platform_admin(user)
    with connect() as conn:
        conn.execute(
            "DELETE FROM ai_provider_key_pool WHERE id = %s",
            (key_id,),
        )


def test_free_provider(provider_code: str, user: CurrentUserResponse) -> dict[str, Any]:
    require_platform_admin(user)
    preset = FREE_PROVIDER_PRESETS.get(provider_code)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provedor gratuito '{provider_code}' não existe no catálogo.",
        )
    settings = get_settings()
    with connect() as conn:
        try:
            result = execute_free_provider_call(
                provider_code=provider_code,
                model_id=preset["default_model"],
                prompt="Responda em uma palavra: 'Ok'",
                settings=settings,
                conn=conn,
            )
            return {
                "ok": True,
                "provider": provider_code,
                "model": preset["default_model"],
                "response": result.get("text", "").strip(),
                "usage": result.get("usage", {}),
            }
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Falha no teste com {preset['name']}: {exc}",
            ) from exc


def get_organization_budget(organization_id: UUID, user: CurrentUserResponse) -> OrganizationBudgetRead:
    require_platform_admin(user)
    with connect() as conn:
        budget_row = conn.execute(
            """
            SELECT organization_id, monthly_token_cap, monthly_cost_cap_cents,
                   alert_threshold_percent, enforce_hard_stop
            FROM ai_organization_budgets
            WHERE organization_id = %s
            """,
            (organization_id,),
        ).fetchone()

        usage_row = conn.execute(
            """
            SELECT 
                COALESCE(SUM((output->'usage'->>'input_units')::bigint + (output->'usage'->>'output_units')::bigint), 0) as tokens_used,
                COALESCE(SUM((output->>'cost_cents')::int), 0) as cost_cents_used
            FROM ai_execution_attempts a
            LEFT JOIN ai_workflow_step_runs s ON s.id = a.step_run_id
            WHERE a.organization_id = %s
              AND a.started_at >= date_trunc('month', now())
              AND a.status = 'completed'
            """,
            (organization_id,),
        ).fetchone()

        tokens_used = int(usage_row["tokens_used"]) if usage_row else 0
        cost_cents_used = int(usage_row["cost_cents_used"]) if usage_row else 0

        if not budget_row:
            return OrganizationBudgetRead(
                organization_id=organization_id,
                monthly_token_cap=None,
                monthly_cost_cap_cents=None,
                alert_threshold_percent=80,
                enforce_hard_stop=False,
                current_month_tokens=tokens_used,
                current_month_cost_cents=cost_cents_used,
            )

        return OrganizationBudgetRead(
            organization_id=budget_row["organization_id"],
            monthly_token_cap=budget_row["monthly_token_cap"],
            monthly_cost_cap_cents=budget_row["monthly_cost_cap_cents"],
            alert_threshold_percent=budget_row["alert_threshold_percent"],
            enforce_hard_stop=budget_row["enforce_hard_stop"],
            current_month_tokens=tokens_used,
            current_month_cost_cents=cost_cents_used,
        )


def update_organization_budget(
    organization_id: UUID,
    payload: OrganizationBudgetUpdate,
    user: CurrentUserResponse,
) -> OrganizationBudgetRead:
    require_platform_admin(user)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO ai_organization_budgets (
                organization_id, monthly_token_cap, monthly_cost_cap_cents,
                alert_threshold_percent, enforce_hard_stop, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (organization_id) DO UPDATE SET
                monthly_token_cap = EXCLUDED.monthly_token_cap,
                monthly_cost_cap_cents = EXCLUDED.monthly_cost_cap_cents,
                alert_threshold_percent = EXCLUDED.alert_threshold_percent,
                enforce_hard_stop = EXCLUDED.enforce_hard_stop,
                updated_at = now()
            """,
            (
                organization_id,
                payload.monthly_token_cap,
                payload.monthly_cost_cap_cents,
                payload.alert_threshold_percent or 80,
                payload.enforce_hard_stop or False,
            ),
        )
    return get_organization_budget(organization_id, user)


def get_usage_analytics(
    organization_id: UUID | None,
    days: int,
    user: CurrentUserResponse,
) -> UsageAnalyticsResponse:
    require_platform_admin(user)
    with connect() as conn:
        query = """
            SELECT 
                to_char(a.started_at, 'YYYY-MM-DD') as day,
                COALESCE(s.model, a.output->'metadata'->>'model', 'indefinido') as model,
                COALESCE(s.provider, a.output->'metadata'->>'provider', 'indefinido') as provider,
                COUNT(*) as calls,
                COALESCE(SUM((a.output->'usage'->>'input_units')::bigint + (a.output->'usage'->>'output_units')::bigint), 0) as tokens,
                COALESCE(SUM((a.output->>'cost_cents')::int), 0) as cost_cents,
                COALESCE(AVG((a.output->>'latency_ms')::int), 0)::int as avg_latency
            FROM ai_execution_attempts a
            LEFT JOIN ai_workflow_step_runs s ON s.id = a.step_run_id
            WHERE a.started_at >= (now() - (interval '1 day' * %s))
        """
        params: list[Any] = [days]
        if organization_id:
            query += " AND a.organization_id = %s"
            params.append(organization_id)
        query += " GROUP BY 1, 2, 3 ORDER BY 1 DESC, 4 DESC"

        rows = conn.execute(query, tuple(params)).fetchall()

        items = [
            UsageAnalyticsItem(
                date=r["day"],
                model=r["model"],
                provider=r["provider"],
                total_calls=int(r["calls"]),
                total_tokens=int(r["tokens"]),
                total_cost_cents=int(r["cost_cents"]),
                avg_latency_ms=int(r["avg_latency"]),
            )
            for r in rows
        ]

        total_tokens_month = sum(i.total_tokens for i in items)
        total_cost_cents_month = sum(i.total_cost_cents for i in items)
        total_calls_month = sum(i.total_calls for i in items)

        return UsageAnalyticsResponse(
            items=items,
            total_tokens_month=total_tokens_month,
            total_cost_cents_month=total_cost_cents_month,
            total_calls_month=total_calls_month,
        )

