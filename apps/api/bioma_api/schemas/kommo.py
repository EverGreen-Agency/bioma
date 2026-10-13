"""Contratos do painel de dados reais e da deduplicação do Kommo."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class KommoRankedItem(BaseModel):
    label: str
    count: int
    share: float


class KommoDashboardTotals(BaseModel):
    leads_all_time: int
    leads: int
    leads_previous: int | None
    open: int
    won: int
    lost: int
    won_value: float
    open_value: float
    with_visit: int
    last_lead_at: int | None
    last_activity_at: int | None


class KommoPipelineStage(BaseModel):
    id: int
    name: str
    kind: str
    count: int


class KommoPipelineSummary(BaseModel):
    id: int
    name: str
    leads: int
    stages: list[KommoPipelineStage]


class KommoTimelineBucket(BaseModel):
    label: str
    range_label: str
    leads: int


class KommoDimension(BaseModel):
    key: str
    label: str
    filled: int
    total: int
    items: list[KommoRankedItem]


class KommoFieldQuality(BaseModel):
    key: str
    label: str
    filled: int
    total: int


class KommoDashboard(BaseModel):
    period_days: int
    totals: KommoDashboardTotals
    pipelines: list[KommoPipelineSummary]
    timeline: list[KommoTimelineBucket]
    dimensions: list[KommoDimension]
    quality: list[KommoFieldQuality]
    loss_reasons: list[KommoRankedItem]
    campaigns: list[KommoRankedItem]


class KommoDashboardResponse(BaseModel):
    """`dashboard` é nulo enquanto a conta nunca foi sincronizada (ou não está conectada)."""

    configured: bool
    subdomain: str | None
    fetched_at: datetime | None
    dashboard: KommoDashboard | None


class KommoDedupRunSummary(BaseModel):
    id: UUID
    subdomain: str
    contacts_scanned: int
    clusters_count: int
    duplicates_count: int
    leads_to_reassign: int
    created_at: datetime
    requested_by_name: str | None = None


class KommoDedupContact(BaseModel):
    id: int
    name: str | None
    created_at: int | None
    leads_count: int


class KommoDedupCluster(BaseModel):
    cluster_id: str
    match_kind: str
    match_reason: str
    master_contact_id: int
    master_name: str
    duplicate_contacts: list[KommoDedupContact]
    leads_to_reassign: int


class KommoDedupRunDetail(BaseModel):
    run: KommoDedupRunSummary
    match_breakdown: list[KommoRankedItem]
    total_clusters: int
    page: int
    page_size: int
    clusters: list[KommoDedupCluster]
