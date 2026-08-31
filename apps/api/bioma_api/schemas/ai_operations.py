from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


BillingMode = Literal["subscription", "api", "hybrid"]
BillingCycle = Literal["monthly", "annual", "custom"]
SubscriptionStatus = Literal["active", "paused", "cancelled"]
QuotaSource = Literal["api", "manual", "configured", "unavailable"]
WorkflowStatus = Literal["draft", "active", "retired"]
WorkflowRunStatus = Literal["pending_approval", "ready", "running", "completed", "failed", "cancelled"]
WorkflowStepStatus = Literal["pending", "running", "waiting_approval", "completed", "failed", "skipped"]


class AiSubscriptionCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    product_name: str = Field(min_length=1, max_length=160)
    billing_mode: BillingMode = "subscription"
    billing_cycle: BillingCycle = "monthly"
    billing_cycle_months: int = Field(default=1, ge=1, le=120)
    amount_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    seats: int = Field(default=1, ge=1, le=10000)
    status: SubscriptionStatus = "active"
    renews_at: date | None = None
    owner_label: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=3000)


class AiSubscriptionUpdate(BaseModel):
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    product_name: str | None = Field(default=None, min_length=1, max_length=160)
    billing_mode: BillingMode | None = None
    billing_cycle: BillingCycle | None = None
    billing_cycle_months: int | None = Field(default=None, ge=1, le=120)
    amount_cents: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    seats: int | None = Field(default=None, ge=1, le=10000)
    status: SubscriptionStatus | None = None
    renews_at: date | None = None
    owner_label: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=3000)


class AiQuotaSnapshotCreate(BaseModel):
    total_units: Decimal | None = Field(default=None, ge=0)
    used_units: Decimal | None = Field(default=None, ge=0)
    unit: str = Field(min_length=1, max_length=80)
    source: QuotaSource
    period_start: date | None = None
    period_end: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class AiQuotaSnapshotSummary(BaseModel):
    id: UUID
    total_units: Decimal | None = None
    used_units: Decimal | None = None
    remaining_units: Decimal | None = None
    unit: str
    source: QuotaSource
    period_start: date | None = None
    period_end: date | None = None
    measured_at: datetime
    notes: str | None = None


class AiSubscriptionSummary(BaseModel):
    id: UUID
    provider: str
    product_name: str
    billing_mode: BillingMode
    billing_cycle: BillingCycle
    billing_cycle_months: int
    amount_cents: int
    monthly_equivalent_cents: int
    currency: str
    seats: int
    status: SubscriptionStatus
    renews_at: date | None = None
    owner_label: str | None = None
    notes: str | None = None
    latest_quota: AiQuotaSnapshotSummary | None = None
    created_at: datetime
    updated_at: datetime


class AiCostTotal(BaseModel):
    currency: str
    committed_monthly_cents: int
    measured_usage_cents: int


class AiUsageEventCreate(BaseModel):
    workspace_id: UUID | None = None
    workflow_run_id: UUID | None = None
    provider: str = Field(min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=160)
    source: str = Field(min_length=1, max_length=120)
    external_event_id: str | None = Field(default=None, max_length=300)
    input_units: int | None = Field(default=None, ge=0)
    output_units: int | None = Field(default=None, ge=0)
    cached_units: int | None = Field(default=None, ge=0)
    unit: str = Field(default="tokens", min_length=1, max_length=80)
    cost_cents: int | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class AiUsageSummary(BaseModel):
    provider: str
    model: str | None = None
    source: str
    events: int
    input_units: int
    output_units: int
    cached_units: int
    known_cost_cents: int
    unknown_cost_events: int
    currency: str


class AiFinOpsDashboard(BaseModel):
    subscriptions: list[AiSubscriptionSummary]
    totals_by_currency: list[AiCostTotal]
    usage_current_month: list[AiUsageSummary]
    generated_at: datetime


class WorkflowStepDefinition(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    interactive: bool = False
    task_kind: str = Field(default="content_draft", pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    capability: str = Field(default="content", min_length=1, max_length=80)


class WorkflowTemplateSummary(BaseModel):
    slug: str
    name: str
    version: int
    description: str
    source_ref: str
    input_schema: dict[str, Any]
    steps: list[WorkflowStepDefinition]


class WorkflowDefinitionSummary(WorkflowTemplateSummary):
    id: UUID
    status: WorkflowStatus
    created_at: datetime


class WorkflowStepRunSummary(BaseModel):
    id: UUID
    step_key: str
    position: int
    name: str
    description: str | None = None
    interactive: bool
    status: WorkflowStepStatus
    task_kind: str | None = None
    capability: str | None = None
    provider: str | None = None
    model: str | None = None
    account_id: UUID | None = None
    model_catalog_id: UUID | None = None
    selection_reason: dict[str, Any] = Field(default_factory=dict)
    attempts: int = 0
    output: dict[str, Any] | None = None
    cost_cents: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WorkflowRunCreate(BaseModel):
    definition_id: UUID
    workspace_id: UUID | None = None
    idempotency_key: str = Field(min_length=8, max_length=160)
    input: dict[str, Any] = Field(default_factory=dict)
    estimated_cost_cents: int | None = Field(default=None, ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)


class WorkflowRunSummary(BaseModel):
    id: UUID
    definition_id: UUID
    definition_slug: str
    definition_name: str
    definition_version: int
    workspace_id: UUID | None = None
    status: WorkflowRunStatus
    idempotency_key: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    current_step_key: str | None = None
    estimated_cost_cents: int | None = None
    actual_cost_cents: int
    currency: str
    approved_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    steps: list[WorkflowStepRunSummary]


class WorkflowStepComplete(BaseModel):
    output: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=160)
    input_units: int | None = Field(default=None, ge=0)
    output_units: int | None = Field(default=None, ge=0)
    cached_units: int | None = Field(default=None, ge=0)
    cost_cents: int | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    external_event_id: str | None = Field(default=None, max_length=300)
