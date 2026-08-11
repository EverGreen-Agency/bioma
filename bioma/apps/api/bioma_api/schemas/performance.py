from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


PerformanceProvider = Literal[
    "google_ads", "ga4", "search_console", "gtm", "meta_ads", "linkedin_ads", "instagram_organic",
    "google_business_profile", "google_adsense", "youtube_organic",
    "tiktok_organic", "tiktok_ads", "linkedin_organic",
    "rd_station_crm", "hubspot",
]
PerformanceConnectionStatus = Literal["active", "inactive", "error"]
PerformanceSyncProvider = Literal[
    "google_ads", "ga4", "search_console", "gtm", "meta_ads", "linkedin_ads", "instagram_organic",
    "google_business_profile", "google_adsense", "youtube_organic",
    "tiktok_organic", "tiktok_ads", "linkedin_organic",
    "rd_station_crm", "hubspot", "all",
]
PerformanceSeverity = Literal["info", "low", "medium", "high", "critical", "warning"]


class PerformanceConnectionSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    # Nulo quando o workspace não tem registro comercial — é o caso da própria
    # Operação EG. O sujeito da conexão é o workspace (migração 0087).
    client_id: UUID | None = None
    provider: PerformanceProvider
    external_account_id: str
    external_parent_id: str | None = None
    display_name: str | None = None
    status: PerformanceConnectionStatus
    credentials_configured: bool
    last_synced_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_message: str | None = None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PerformanceConnectionCreateRequest(BaseModel):
    provider: PerformanceProvider
    external_account_id: str
    external_parent_id: str | None = None
    display_name: str | None = None
    status: PerformanceConnectionStatus = "active"
    credentials_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerformanceConnectionUpdateRequest(BaseModel):
    external_account_id: str | None = None
    external_parent_id: str | None = None
    display_name: str | None = None
    status: PerformanceConnectionStatus | None = None
    credentials_ref: str | None = None
    metadata: dict[str, Any] | None = None


class SourceFreshnessSummary(BaseModel):
    provider: PerformanceProvider
    status: PerformanceConnectionStatus
    last_synced_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_message: str | None = None


class AdsAccountSummary(BaseModel):
    impressions: int = 0
    clicks: int = 0
    cost_micros: int = 0
    conversions: float = 0
    conversion_value: float = 0
    ctr: float = 0
    cpc_micros: float = 0
    cpa_micros: float = 0
    roas: float = 0


class AdsDailyPoint(BaseModel):
    date: date
    impressions: int
    clicks: int
    cost_micros: int
    conversions: float
    conversion_value: float


class AdsCampaignSummary(BaseModel):
    campaign_id: str
    campaign_name: str
    campaign_status: str
    channel_type: str
    budget_micros: int | None = None
    impressions: int
    clicks: int
    cost_micros: int
    conversions: float
    conversion_value: float
    # Fracao dos leiloes elegiveis em que o anuncio apareceu (0-1). None quando
    # o Google nao reporta o periodo — nunca 0, que significaria "nunca apareceu".
    search_impression_share: float | None = None
    ctr: float
    cpa_micros: float
    roas: float


class Ga4AcquisitionSummary(BaseModel):
    source: str
    medium: str
    campaign: str
    sessions: int
    total_users: int
    new_users: int
    engaged_sessions: int
    engagement_rate: float
    key_events: float


class GscQuerySummary(BaseModel):
    query: str
    country: str
    device: str
    clicks: float
    impressions: float
    ctr: float
    position: float


class TrackingFindingSummary(BaseModel):
    id: UUID
    code: str
    title: str
    description: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    status: Literal["open", "resolved", "ignored"]
    created_at: datetime


class GtmSnapshotSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    collected_at: datetime
    account_id: str
    container_id: str
    gtm_workspace_id: str | None = None
    published_version: str | None = None
    tags_count: int
    triggers_count: int
    variables_count: int
    findings: list[TrackingFindingSummary]


class PerformanceInsightSummary(BaseModel):
    id: UUID
    source: str
    category: str
    severity: Literal["info", "warning", "critical"]
    title: str
    description: str
    recommendation: str | None = None
    period_start: date
    period_end: date
    current_value: float | None = None
    comparison_value: float | None = None
    status: Literal["active", "archived", "resolved"]
    created_at: datetime


class PerformanceSyncRunEntry(BaseModel):
    """Uma execucao de sync, com o ERRO quando houve.

    Existe porque `POST /sync` pedia e nada devolvia o resultado: o sintoma de
    uma conexao mal configurada era silencio total na tela."""

    id: UUID
    provider: str | None = None
    status: str
    error_code: str | None = None
    error_message: str | None = None
    records_processed: int = 0
    started_at: datetime
    finished_at: datetime | None = None


class PerformanceOverviewResponse(BaseModel):
    workspace_id: UUID
    # Nulo no workspace da agência, que não tem registro comercial. Quem
    # identifica a visão é `workspace_id`.
    client_id: UUID | None = None
    period_start: date
    period_end: date
    freshness: list[SourceFreshnessSummary]
    ads: AdsAccountSummary
    daily: list[AdsDailyPoint]
    insights: list[PerformanceInsightSummary]


class PerformanceSyncRequest(BaseModel):
    provider: PerformanceSyncProvider = "all"
    date_from: date | None = None
    date_to: date | None = None


class PerformanceSyncRunSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    source: str
    provider: str | None = None
    status: Literal["queued", "running", "ok", "error", "partial"]
    summary: dict[str, Any]
    date_from: date | None = None
    date_to: date | None = None
    records_processed: int
    started_at: datetime
    finished_at: datetime | None = None
