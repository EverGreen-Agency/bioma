from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.db import connect
from bioma_api.repositories import ai_routing as repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.schemas.ai_routing import (
    AiRoutingControlPlane,
    ModelCatalogSummary,
    ModelCatalogUpsert,
    ProviderAccountCreate,
    ProviderAccountSummary,
    ProviderAccountUpdate,
    QuotaBucketCreate,
    QuotaBucketSummary,
    QuotaCollectionJobSummary,
    RouteCandidate,
    RoutePreview,
    RoutePreviewRequest,
    RoutingPolicySummary,
    RoutingPolicyUpsert,
    WebSessionConnectPayload,
)
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services.ai_operations import _eg_organization_id


MODEL_PRESETS: dict[str, list[dict[str, Any]]] = {
    "codex_chatgpt": [
        {
            "model_id": "gpt-5.6-luna",
            "display_name": "GPT-5.6 Luna",
            "family": "gpt-5.6",
            "capability_tier": "economy",
            "capabilities": ["chat", "content", "code", "structured_output"],
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
            "capabilities": ["chat", "content", "strategy", "code", "tools", "structured_output"],
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
            "capabilities": ["chat", "content", "strategy", "code", "tools", "structured_output"],
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
            "capabilities": ["chat", "content", "code", "structured_output"],
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
            "capabilities": ["chat", "content", "strategy", "code", "tools", "structured_output"],
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
            "capabilities": ["chat", "content", "strategy", "code", "tools", "structured_output"],
            "quality_score": 98,
            "cost_score": 35,
            "latency_score": 50,
            "priority": 10,
        },
    ],
    "antigravity_cli": [
        {
            "model_id": "gemini-3.6-flash",
            "display_name": "Gemini 3.6 Flash",
            "family": "gemini",
            "capability_tier": "economy",
            "capabilities": ["chat", "content", "code", "tools", "multimodal"],
            "quality_score": 82,
            "cost_score": 92,
            "latency_score": 94,
            "priority": 30,
        },
        {
            "model_id": "gemini-3.1-pro",
            "display_name": "Gemini 3.1 Pro",
            "family": "gemini",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "tools", "multimodal"],
            "quality_score": 96,
            "cost_score": 48,
            "latency_score": 58,
            "priority": 10,
        },
        {
            "model_id": "claude-sonnet-4.6",
            "display_name": "Claude Sonnet 4.6 (Thinking)",
            "family": "claude",
            "capability_tier": "balanced",
            "capabilities": ["chat", "content", "strategy", "code", "tools"],
            "quality_score": 92,
            "cost_score": 65,
            "latency_score": 70,
            "priority": 20,
        },
        {
            "model_id": "claude-opus-4.6",
            "display_name": "Claude Opus 4.6 (Thinking)",
            "family": "claude",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "tools"],
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
            "capabilities": ["chat", "content", "code"],
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
            "capabilities": ["chat", "content", "code", "tools", "multimodal", "structured_output"],
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
            "capabilities": ["chat", "content", "strategy", "code", "tools", "multimodal", "structured_output"],
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
            "capabilities": ["chat", "content", "code", "tools"],
            "quality_score": 85,
            "cost_score": 85,
            "latency_score": 85,
            "priority": 10,
        },
        {
            "model_id": "anthropic/claude-3.5-sonnet:beta",
            "display_name": "Claude 3.5 Sonnet (OpenRouter)",
            "family": "claude",
            "capability_tier": "frontier",
            "capabilities": ["chat", "content", "strategy", "code", "tools"],
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
            "model_id": "deepseek-reasoner",
            "display_name": "DeepSeek R1 (Reasoner)",
            "family": "deepseek",
            "capability_tier": "frontier",
            "capabilities": ["reasoning", "strategy", "code"],
            "quality_score": 98,
            "cost_score": 92,
            "latency_score": 60,
            "priority": 10,
        },
        {
            "model_id": "deepseek-chat",
            "display_name": "DeepSeek V3 (Chat & Tools)",
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


def connect_web_session(
    account_id: UUID,
    payload: WebSessionConnectPayload,
    user: CurrentUserResponse,
) -> AiRoutingControlPlane:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        if not repo.connect_web_session(conn, organization_id, account_id, user.id, payload.model_dump(exclude_unset=True)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta de IA não encontrada.")
            
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.provider_account.connected",
            {"account_id": str(account_id), "method": "web_session"},
        )
    
    # Após conectar a sessão com sucesso, vamos tentar preencher os modelos iniciais do canal
    try:
        return bootstrap_models(account_id, user)
    except HTTPException:
        # Se o canal não possuir modelos pré-configurados, retornamos normalmente
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
                    "Coleta automática está disponível apenas para contas codex_chatgpt. "
                    "Claude Code e Antigravity CLI expõem a cota em UI/TUI; registre um snapshot manual."
                ),
            )
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "ai.quota_collection.queued",
            {"account_id": str(account_id), "job_id": str(row["id"]), "collector": "codex_app_server"},
        )
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
            if account.execution_mode == "manual_handoff":
                eligible = False
                reasons.append("canal exige handoff manual")
            if account.channel == "antigravity_cli":
                eligible = False
                reasons.append("CLI não possui execução headless documentada; use antigravity_sdk")
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
