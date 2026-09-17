from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


GenerationMode = Literal["live", "preview", "manual"]
ResearchStatus = Literal["running", "completed", "failed", "archived"]


class MarketResearchRefineRequest(BaseModel):
    sector: str = Field(min_length=2, max_length=120)
    objective: str | None = Field(default=None, max_length=2_000)
    geographic_scope: str = Field(default="Brasil", min_length=2, max_length=120)


class MarketResearchFocusOption(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_]+$")
    label: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=2, max_length=600)


class MarketResearchRefinement(BaseModel):
    sector_interpretation: str = Field(min_length=2, max_length=600)
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    focus_options: list[MarketResearchFocusOption] = Field(min_length=3, max_length=12)
    generation_mode: GenerationMode


class MarketResearchCreate(BaseModel):
    sector: str = Field(min_length=2, max_length=120)
    objective: str | None = Field(default=None, max_length=2_000)
    geographic_scope: str = Field(default="Brasil", min_length=2, max_length=120)
    selected_focus: list[MarketResearchFocusOption] = Field(min_length=1, max_length=12)


class ResearchMarketOverview(BaseModel):
    description: str
    market_size_and_segments: list[str]
    business_models: list[str]
    growth_outlook: str
    trends: list[str]
    source_urls: list[str] = Field(default_factory=list)


class ResearchCommercialProcess(BaseModel):
    sales_strategies: list[str]
    acquisition_and_retention: list[str]
    buying_journey: list[str]
    qualification_signals: list[str]
    source_urls: list[str] = Field(default_factory=list)


class ResearchChallenge(BaseModel):
    challenge: str
    business_impact: str
    opportunity: str
    source_urls: list[str] = Field(default_factory=list)


class ResearchMarketLeader(BaseModel):
    name: str
    segment: str
    success_strategy: str
    source_urls: list[str] = Field(default_factory=list)


class ResearchTerminology(BaseModel):
    term: str
    definition: str
    source_urls: list[str] = Field(default_factory=list)


class ResearchGrowthOpportunity(BaseModel):
    opportunity: str
    recommended_service: str
    rationale: str
    priority: Literal["high", "medium", "low"]
    source_urls: list[str] = Field(default_factory=list)


class ResearchProspectingPlaybook(BaseModel):
    opening_angles: list[str]
    qualification_questions: list[str]
    likely_objections: list[str]
    credibility_cautions: list[str]


class ResearchContentOpportunity(BaseModel):
    theme: str
    recommended_format: str
    funnel_stage: Literal["awareness", "consideration", "decision", "retention"]
    rationale: str
    source_urls: list[str] = Field(default_factory=list)


class MarketResearchSource(BaseModel):
    url: HttpUrl
    title: str | None = None
    publisher: str | None = None
    publication_date: date | None = None
    consulted_at: datetime | None = None


class MarketResearchReport(BaseModel):
    title: str
    executive_summary: str
    market_overview: ResearchMarketOverview
    commercial_process: ResearchCommercialProcess
    challenges: list[ResearchChallenge]
    market_leaders: list[ResearchMarketLeader]
    terminology: list[ResearchTerminology]
    growth_opportunities: list[ResearchGrowthOpportunity]
    prospecting_playbook: ResearchProspectingPlaybook
    content_opportunities: list[ResearchContentOpportunity]
    caveats: list[str]
    sources: list[MarketResearchSource] = Field(default_factory=list)


class MarketResearchSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    version: int
    sector: str
    geographic_scope: str
    objective: str | None = None
    selected_focus: list[MarketResearchFocusOption]
    status: ResearchStatus
    generation_mode: GenerationMode
    provider: str | None = None
    model: str | None = None
    token_usage: dict
    estimated_cost_cents: int | None = None
    source_count: int
    error_message: str | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MarketResearchDetail(MarketResearchSummary):
    report: MarketResearchReport | None = None
    sources: list[MarketResearchSource] = Field(default_factory=list)
