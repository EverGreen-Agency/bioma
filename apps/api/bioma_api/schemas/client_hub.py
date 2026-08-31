from datetime import date, datetime
from uuid import UUID

from typing import Any, Literal

from pydantic import BaseModel, Field

ClientStatus = Literal["onboarding", "active", "paused", "completed", "archived"]
ArtifactVisibility = Literal["internal", "client"]
DeliverableStatus = Literal["planned", "in_progress", "waiting_approval", "done", "blocked"]
ApprovalStatus = Literal["pending", "approved", "rejected", "cancelled"]
LeadStage = Literal["new", "qualifying", "meeting", "proposal", "won", "lost"]
FinancialRecordKind = Literal["contract", "invoice"]
FinancialRecordStatus = Literal["draft", "open", "paid", "overdue", "cancelled"]
ClientRequestCategory = Literal["request", "question", "change", "input"]
ClientRequestStatus = Literal["submitted", "triaged", "in_progress", "waiting_client", "done", "declined"]


class ClientSummary(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    organization_slug: str
    name: str
    status: ClientStatus
    responsible_name: str | None = None
    enabled_modules: list[str] = []
    deliverables_total: int
    approvals_pending: int
    artifacts_client: int


class ArtifactSummary(BaseModel):
    id: UUID
    title: str
    kind: str
    visibility: ArtifactVisibility
    url: str | None = None
    content: str | None = None
    created_at: datetime


class DeliverableSummary(BaseModel):
    id: UUID
    title: str
    status: DeliverableStatus
    due_at: datetime | None = None
    assignee_emails: list[str] = []
    updated_at: datetime


class GlobalDeliverableSummary(DeliverableSummary):
    client_id: UUID
    client_name: str


class ApprovalSummary(BaseModel):
    id: UUID
    deliverable_id: UUID | None = None
    deliverable_title: str | None = None
    status: ApprovalStatus
    comment: str | None = None
    created_at: datetime
    decided_at: datetime | None = None


class SyncRunSummary(BaseModel):
    id: UUID
    source: str
    status: Literal["queued", "running", "ok", "error", "partial"]
    summary: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None = None


class AuditLogSummary(BaseModel):
    id: UUID
    event_type: str
    actor_user_id: UUID | None = None
    metadata: dict[str, Any]
    created_at: datetime


class ClientRequestCreate(BaseModel):
    category: ClientRequestCategory = "request"
    title: str = Field(min_length=2, max_length=300)
    detail: str | None = Field(default=None, max_length=5_000)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


class ClientRequestUpdate(BaseModel):
    status: ClientRequestStatus | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    assigned_to: UUID | None = None
    resolution_summary: str | None = Field(default=None, max_length=5_000)


class ClientRequestSummary(BaseModel):
    id: UUID
    category: ClientRequestCategory
    title: str
    detail: str | None = None
    status: ClientRequestStatus
    priority: Literal["low", "normal", "high", "urgent"]
    requested_by: UUID | None = None
    requested_by_name: str | None = None
    assigned_to: UUID | None = None
    resolution_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class ClientAttentionItem(BaseModel):
    kind: Literal["approval", "request", "delivery"]
    entity_id: UUID
    title: str
    detail: str
    action_label: str
    due_at: datetime | None = None


class ClientProgressSummary(BaseModel):
    deliverables_total: int
    deliverables_done: int
    deliverables_in_progress: int
    completion_percentage: int


class ClientPortalResponse(BaseModel):
    client: ClientSummary
    attention: list[ClientAttentionItem] = []
    progress: ClientProgressSummary
    requests: list[ClientRequestSummary] = []
    artifacts: list[ArtifactSummary]
    deliverables: list[DeliverableSummary]
    approvals: list[ApprovalSummary]
    sync_runs: list[SyncRunSummary]
    audit_logs: list[AuditLogSummary]


class ClientCreateRequest(BaseModel):
    name: str
    organization_name: str | None = None
    organization_slug: str | None = None
    status: ClientStatus = "onboarding"
    responsible_name: str | None = None


class ClientUpdateRequest(BaseModel):
    name: str | None = None
    organization_name: str | None = None
    status: ClientStatus | None = None
    responsible_name: str | None = None
    enabled_modules: list[str] | None = None


class ClientPurgeRequest(BaseModel):
    confirmation: str


class ArtifactCreateRequest(BaseModel):
    title: str
    kind: str
    visibility: ArtifactVisibility = "client"
    content: str | None = None
    url: str | None = None


class ArtifactUpdateRequest(BaseModel):
    title: str | None = None
    kind: str | None = None
    visibility: ArtifactVisibility | None = None
    content: str | None = None
    url: str | None = None


class DeliverableCreateRequest(BaseModel):
    title: str
    status: DeliverableStatus = "planned"
    due_at: datetime | None = None


class DeliverableUpdateRequest(BaseModel):
    title: str | None = None
    status: DeliverableStatus | None = None
    due_at: datetime | None = None


class ApprovalCreateRequest(BaseModel):
    deliverable_id: UUID
    comment: str | None = None


class ApprovalDecisionRequest(BaseModel):
    status: Literal["approved", "rejected", "cancelled"]
    comment: str | None = None


class DeliverableStatusRequest(BaseModel):
    status: DeliverableStatus


class LeadSummary(BaseModel):
    id: UUID
    name: str
    company: str | None = None
    role_title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    source: str | None = None
    stage: LeadStage
    expected_value: float | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadCreateRequest(BaseModel):
    name: str
    company: str | None = None
    role_title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    source: str | None = None
    stage: LeadStage = "new"
    expected_value: float | None = None
    notes: str | None = None


class LeadUpdateRequest(BaseModel):
    name: str | None = None
    company: str | None = None
    role_title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    source: str | None = None
    stage: LeadStage | None = None
    expected_value: float | None = None
    notes: str | None = None


class FinancialRecordSummary(BaseModel):
    id: UUID
    kind: FinancialRecordKind
    title: str
    amount: float | None = None
    currency: str
    status: FinancialRecordStatus
    contract_start_at: date | None = None
    contract_end_at: date | None = None
    due_at: date | None = None
    paid_at: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CockpitOverdueItem(BaseModel):
    id: UUID
    title: str
    status: DeliverableStatus
    due_at: datetime
    client_id: UUID
    client_name: str


class CockpitPendingApproval(BaseModel):
    id: UUID
    deliverable_title: str | None = None
    created_at: datetime
    client_id: UUID
    client_name: str


class PortfolioPerformanceRow(BaseModel):
    """Uma linha por cliente: investimento por canal e leads no período."""
    client_id: UUID
    client_name: str
    workspace_id: UUID
    status: ClientStatus
    google_spend_cents: int
    meta_spend_cents: int
    linkedin_spend_cents: int
    total_spend_cents: int
    total_leads: int
    # Meta do mês corrente (monthly_targets). None = meta não definida — o
    # painel mostra "—" em vez de fingir que a meta é zero.
    target_leads: float | None = None
    budget_cents: int | None = None


class MonthlyTargetRequest(BaseModel):
    target_leads: float | None = None
    budget_cents: int | None = None


class CockpitStaleConnection(BaseModel):
    """Integração ativa que parou de sincronizar. `days_stale` é None quando a
    conexão nunca sincronizou — ausência de sync, não zero dias."""
    client_id: UUID
    client_name: str
    provider: str
    display_name: str | None = None
    last_synced_at: datetime | None = None
    last_error_message: str | None = None
    days_stale: int | None = None


class CockpitPortfolioSummary(BaseModel):
    monthly_revenue_cents: int
    mrr_cents: int
    overdue_deliverables: int
    clients_at_risk: int
    clients_active: int
    clients_total: int
    overdue_items: list[CockpitOverdueItem] = []
    pending_approvals: list[CockpitPendingApproval] = []
    stale_connections: list[CockpitStaleConnection] = []
    radar_prospects_awaiting: int = 0


class FinancialRecordCreateRequest(BaseModel):
    kind: FinancialRecordKind
    title: str
    amount: float | None = None
    currency: str = "BRL"
    status: FinancialRecordStatus = "open"
    contract_start_at: date | None = None
    contract_end_at: date | None = None
    due_at: date | None = None
    paid_at: date | None = None
    notes: str | None = None


class FinancialRecordUpdateRequest(BaseModel):
    kind: FinancialRecordKind | None = None
    title: str | None = None
    amount: float | None = None
    currency: str | None = None
    status: FinancialRecordStatus | None = None
    contract_start_at: date | None = None
    contract_end_at: date | None = None
    due_at: date | None = None
    paid_at: date | None = None
    notes: str | None = None


class PerformanceMetricSummary(BaseModel):
    id: UUID
    period_start: date
    period_end: date
    channel: str
    metric: str
    value: float
    source: str
    notes: str | None = None
    captured_at: datetime


class PerformanceMetricCreateRequest(BaseModel):
    period_start: date
    period_end: date
    channel: str
    metric: str
    value: float
    source: str = "manual"
    notes: str | None = None


class PerformanceMetricUpdateRequest(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    channel: str | None = None
    metric: str | None = None
    value: float | None = None
    source: str | None = None
    notes: str | None = None


class DailyBriefItem(BaseModel):
    """Uma linha do resumo diário (decisão 3)."""

    kind: str
    severity: Literal["critical", "warning", "info"]
    title: str
    detail: str
    count: int
    # No máximo 3. O card é um resumo — listar tudo o transformaria na própria
    # tela que ele deveria resumir.
    examples: list[str] = []
    href: str


class DailyBrief(BaseModel):
    generated_at: datetime
    # True = nada pendente. A tela mostra isso em vez de inventar assunto:
    # resumo que fala todo dia treina a pessoa a fechar sem ler.
    clear: bool
    items: list[DailyBriefItem] = []
