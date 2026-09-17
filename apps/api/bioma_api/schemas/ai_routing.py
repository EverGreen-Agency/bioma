from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


Provider = Literal["openai", "anthropic", "google", "openrouter", "deepseek", "groq"]
AuthMode = Literal[
    "chatgpt",
    "claude_subscription",
    "google_subscription",
    "api_key",
    "vertex_adc",
    "service_account",
]
ExecutionMode = Literal["app_server", "local_cli", "sdk", "api", "manual_handoff"]
AccountStatus = Literal["active", "degraded", "unavailable", "paused"]
QuotaSource = Literal[
    "provider_api",
    "provider_cli",
    "provider_ui",
    "bioma_metered",
    "configured",
    "unavailable",
]
QuotaConfidence = Literal["authoritative", "measured", "manual", "unavailable"]
CapabilityTier = Literal["economy", "balanced", "frontier", "specialist"]


class ProviderAccountCreate(BaseModel):
    subscription_id: UUID | None = None
    provider: Provider
    channel: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=160)
    auth_mode: AuthMode
    execution_mode: ExecutionMode
    auth_ref: str | None = Field(default=None, max_length=300)
    status: AccountStatus = "active"
    is_default: bool = False
    capabilities: list[str] = Field(default_factory=list, max_length=40)
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_channel_contract(self):
        if self.channel == "antigravity_cli" and self.execution_mode not in {"local_cli", "manual_handoff"}:
            raise ValueError(
                "Antigravity CLI deve usar local_cli para execução headless ou manual_handoff."
            )
        if self.auth_ref and not self.auth_ref.startswith(("env:", "vault:")):
            raise ValueError("auth_ref deve usar env:NOME ou vault:IDENTIFICADOR.")
        return self


class ProviderAccountUpdate(BaseModel):
    subscription_id: UUID | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    auth_mode: AuthMode | None = None
    execution_mode: ExecutionMode | None = None
    auth_ref: str | None = Field(default=None, max_length=300)
    status: AccountStatus | None = None
    is_default: bool | None = None
    capabilities: list[str] | None = Field(default=None, max_length=40)
    settings: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_auth_ref(self):
        if self.auth_ref and not self.auth_ref.startswith(("env:", "vault:")):
            raise ValueError("auth_ref deve usar env:NOME ou vault:IDENTIFICADOR.")
        return self


class ModelCatalogUpsert(BaseModel):
    model_id: str = Field(min_length=1, max_length=180)
    display_name: str = Field(min_length=1, max_length=180)
    family: str | None = Field(default=None, max_length=120)
    capability_tier: CapabilityTier = "balanced"
    capabilities: list[str] = Field(default_factory=list, max_length=40)
    quality_score: int = Field(default=50, ge=0, le=100)
    cost_score: int = Field(default=50, ge=0, le=100)
    latency_score: int = Field(default=50, ge=0, le=100)
    context_window: int | None = Field(default=None, gt=0)
    enabled: bool = True
    priority: int = Field(default=100, ge=0, le=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuotaBucketCreate(BaseModel):
    bucket_key: str = Field(min_length=1, max_length=120)
    scope: Literal["account", "workspace", "model", "model_family", "credits"] = "account"
    model_id: str | None = Field(default=None, max_length=180)
    total_units: Decimal | None = Field(default=None, ge=0)
    used_units: Decimal | None = Field(default=None, ge=0)
    used_percent: Decimal | None = Field(default=None, ge=0, le=100)
    remaining_percent: Decimal | None = Field(default=None, ge=0, le=100)
    unit: str = Field(default="percent", min_length=1, max_length=80)
    window_duration_minutes: int | None = Field(default=None, gt=0)
    resets_at: datetime | None = None
    source: QuotaSource
    confidence: QuotaConfidence
    measured_at: datetime | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def derive_percentages(self):
        if self.used_percent is None and self.remaining_percent is not None:
            self.used_percent = Decimal(100) - self.remaining_percent
        if self.remaining_percent is None and self.used_percent is not None:
            self.remaining_percent = Decimal(100) - self.used_percent
        if (
            self.used_percent is None
            and self.total_units not in (None, Decimal(0))
            and self.used_units is not None
        ):
            used = min((self.used_units / self.total_units) * Decimal(100), Decimal(100))
            self.used_percent = used
            self.remaining_percent = Decimal(100) - used
        return self


class RoutingPolicyUpsert(BaseModel):
    task_kind: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    capability: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    allowed_channels: list[str] = Field(default_factory=list, max_length=30)
    allowed_models: list[str] = Field(default_factory=list, max_length=50)
    preferred_tiers: list[CapabilityTier] = Field(default_factory=list)
    quality_weight: int = Field(default=35, ge=0, le=100)
    quota_weight: int = Field(default=25, ge=0, le=100)
    cost_weight: int = Field(default=20, ge=0, le=100)
    reliability_weight: int = Field(default=10, ge=0, le=100)
    latency_weight: int = Field(default=10, ge=0, le=100)
    minimum_quota_headroom: Decimal = Field(default=10, ge=0, le=100)
    requires_human_approval: bool = True
    allow_fallback: bool = True
    status: Literal["draft", "active", "retired"] = "active"

    @model_validator(mode="after")
    def validate_weights(self):
        total = (
            self.quality_weight
            + self.quota_weight
            + self.cost_weight
            + self.reliability_weight
            + self.latency_weight
        )
        if total != 100:
            raise ValueError("Os pesos de roteamento devem somar 100.")
        return self


class QuotaBucketSummary(BaseModel):
    id: UUID
    bucket_key: str
    scope: str
    model_id: str | None = None
    total_units: Decimal | None = None
    used_units: Decimal | None = None
    used_percent: Decimal | None = None
    remaining_percent: Decimal | None = None
    unit: str
    window_duration_minutes: int | None = None
    resets_at: datetime | None = None
    source: QuotaSource
    confidence: QuotaConfidence
    measured_at: datetime
    raw_metadata: dict[str, Any]
    notes: str | None = None


class ModelCatalogSummary(BaseModel):
    id: UUID
    account_id: UUID
    model_id: str
    display_name: str
    family: str | None = None
    capability_tier: CapabilityTier
    capabilities: list[str]
    quality_score: int
    cost_score: int
    latency_score: int
    context_window: int | None = None
    enabled: bool
    priority: int
    metadata: dict[str, Any]
    discovered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProviderAccountSummary(BaseModel):
    id: UUID
    subscription_id: UUID | None = None
    provider: Provider
    channel: str
    display_name: str
    auth_mode: AuthMode
    execution_mode: ExecutionMode
    auth_ref: str | None = None
    status: AccountStatus
    is_default: bool
    capabilities: list[str]
    settings: dict[str, Any]
    health_detail: str | None = None
    last_probe_at: datetime | None = None
    credentials_configured: bool = False
    models: list[ModelCatalogSummary]
    quota_buckets: list[QuotaBucketSummary]
    created_at: datetime
    updated_at: datetime


class RoutingPolicySummary(RoutingPolicyUpsert):
    id: UUID
    created_at: datetime
    updated_at: datetime


class HarnessConfigUpsert(BaseModel):
    planner_model_catalog_id: UUID | None = None
    tool_caller_model_catalog_id: UUID | None = None
    auditor_model_catalog_id: UUID | None = None
    curator_model_catalog_id: UUID | None = None
    enabled_tools: list[str] = Field(default_factory=list, max_length=80)


class HarnessConfigSummary(HarnessConfigUpsert):
    organization_id: UUID
    created_at: datetime
    updated_at: datetime


class QuotaCollectionJobSummary(BaseModel):
    id: UUID
    account_id: UUID
    collector: str
    status: Literal["queued", "running", "completed", "failed"]
    result: dict[str, Any] | None = None
    error_message: str | None = None
    attempts: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class ProviderRuntimeStatus(BaseModel):
    account_id: UUID
    channel: str
    runtime_surface: Literal["api", "worker"]
    installed: bool
    authenticated: bool
    ready: bool
    version: str | None = None
    auth_method: str | None = None
    detail: str
    instructions: list[str] = Field(default_factory=list)
    checked_at: datetime


class ProviderLoginInput(BaseModel):
    value: str = Field(min_length=1, max_length=2000)


class ProviderLoginSession(BaseModel):
    id: UUID
    organization_id: UUID
    account_id: UUID
    channel: str
    account_name: str
    status: Literal["pending", "running", "waiting_input", "completed", "failed", "canceled", "expired"]
    public_output: str
    prompt_hint: str | None = None
    error_message: str | None = None
    expires_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RoutePreviewRequest(BaseModel):
    task_kind: str = Field(min_length=1, max_length=80)
    capability: str | None = Field(default=None, max_length=80)


class RouteCandidate(BaseModel):
    account_id: UUID
    model_catalog_id: UUID
    provider: Provider
    channel: str
    model_id: str
    display_name: str
    score: Decimal
    quota_headroom: Decimal | None = None
    eligible: bool
    reasons: list[str]


class RoutePreview(BaseModel):
    task_kind: str
    policy_id: UUID | None = None
    selected: RouteCandidate | None = None
    candidates: list[RouteCandidate]


class AiRoutingControlPlane(BaseModel):
    accounts: list[ProviderAccountSummary]
    policies: list[RoutingPolicySummary]
    harness_config: HarnessConfigSummary | None = None
    quota_collection_jobs: list[QuotaCollectionJobSummary] = Field(default_factory=list)
    generated_at: datetime
