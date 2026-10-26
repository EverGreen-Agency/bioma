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
    stale_open: int = 0
    without_rep: int = 0


class KommoUfCount(BaseModel):
    label: str
    count: int


class KommoRepSummary(BaseModel):
    label: str
    leads: int
    open: int
    won: int
    lost: int
    stale_open: int
    won_value: float
    ufs: list[KommoUfCount]


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


class NomusRepSales(BaseModel):
    label: str
    territorio: str | None = None
    faturamento: float
    pedidos: int
    share: float


class NomusTopProduct(BaseModel):
    label: str
    quantidade: int
    valor_estimado: float


class NomusAnalyticsSummary(BaseModel):
    configured: bool = True
    faturamento_total: float = 0.0
    pedidos_count: int = 0
    ticket_medio: float = 0.0
    representantes_count: int = 0
    reps: list[NomusRepSales] = []
    top_products: list[NomusTopProduct] = []


class KommoDashboard(BaseModel):
    period_days: int
    totals: KommoDashboardTotals
    pipelines: list[KommoPipelineSummary]
    timeline: list[KommoTimelineBucket]
    dimensions: list[KommoDimension]
    quality: list[KommoFieldQuality]
    loss_reasons: list[KommoRankedItem]
    campaigns: list[KommoRankedItem]
    stale_after_days: int = 7
    reps: list[KommoRepSummary] = []
    nomus: NomusAnalyticsSummary | None = None


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
