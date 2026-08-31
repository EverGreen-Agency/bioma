from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SocialDailyMetric(BaseModel):
    id: UUID
    workspace_id: UUID
    client_id: UUID | None = None
    date: date
    account_id: str | None = None
    account_name: str | None = None
    campaign_id: str
    campaign_name: str
    impressions: int
    clicks: int
    spend_cents: int
    conversions: int
    leads: int
    revenue_cents: int
    ctr: float = 0.0
    cpc_cents: int = 0
    cpa_cents: int = 0
    roas: float = 0.0
    created_at: datetime


class PerformanceAiSummaryInsight(BaseModel):
    channel: str  # "meta_ads", "linkedin_ads", "google_ads", "multichannel"
    title: str
    finding: str
    action_recommendation: str
    impact_level: str  # "high", "medium", "low"


class PerformanceAiSummaryResponse(BaseModel):
    workspace_id: UUID
    generated_at: datetime
    summary_text: str
    total_spend_cents: int
    total_leads: int
    overall_cpa_cents: int
    # `live` = o modelo leu os números. `preview` = sem chave de IA, a resposta
    # organiza os números sem sintetizar. `unavailable` = a chamada falhou e os
    # números continuam valendo. A tela precisa dizer qual foi — chamar prévia
    # de análise foi exatamente o problema que esta feature corrigiu.
    generation_mode: str = "preview"
    insights: list[PerformanceAiSummaryInsight]
