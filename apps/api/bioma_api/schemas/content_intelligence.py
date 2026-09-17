from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

HookSource = Literal["llm_transcript", "higgsfield_virality"]
ScriptStatus = Literal["suggested", "approved", "scheduled", "recorded", "published", "discarded"]


class InstagramPostSummary(BaseModel):
    id: UUID
    ig_media_id: str
    permalink: str | None = None
    media_type: str
    caption: str | None = None
    posted_at: datetime | None = None
    thumbnail_url: str | None = None
    reach: int
    impressions: int
    likes: int
    comments: int
    shares: int
    saved: int
    plays: int
    avg_watch_time_seconds: float | None = None
    transcript: str | None = None
    source_script_id: UUID | None = None


class HookAnalysisSummary(BaseModel):
    id: UUID
    post_id: UUID
    source: HookSource
    hook_text: str | None = None
    hook_pattern: str | None = None
    effectiveness_score: float | None = None
    analysis_notes: str | None = None
    created_at: datetime


class ContentRetrospectiveSummary(BaseModel):
    id: UUID
    period_start: date
    period_end: date
    posts_analyzed: int
    generation_mode: str
    output_data: dict[str, Any]
    token_usage: dict[str, Any]
    estimated_cost_cents: int
    created_at: datetime


class ContentScriptSummary(BaseModel):
    id: UUID
    retrospective_id: UUID | None = None
    title: str
    theme: str | None = None
    hook_opening: str | None = None
    script_body: str
    suggested_format: str | None = None
    cta: str | None = None
    rationale: str | None = None
    status: ScriptStatus
    scheduled_for: date | None = None
    generation_mode: str
    created_at: datetime
    updated_at: datetime


class ScriptScoreboardRow(BaseModel):
    script_id: UUID
    title: str
    theme: str | None = None
    suggested_format: str | None = None
    posts: int
    avg_reach: float
    avg_engagement: float


class ScriptScoreboard(BaseModel):
    """Placar: roteiro da IA x resto da conta. `lift_*` e None quando falta base
    de comparacao (nenhum post vinculado, ou nenhum post organico fora da IA)."""
    period_start: date
    period_end: date
    ai_posts: int
    other_posts: int
    ai_avg_reach: float | None = None
    other_avg_reach: float | None = None
    ai_avg_engagement: float | None = None
    other_avg_engagement: float | None = None
    ai_avg_saved: float | None = None
    other_avg_saved: float | None = None
    lift_reach_percent: float | None = None
    lift_engagement_percent: float | None = None
    per_script: list[ScriptScoreboardRow] = []


class GenerateRetrospectiveRequest(BaseModel):
    period_days: int = Field(default=60, ge=7, le=180)


class GenerateScriptsRequest(BaseModel):
    count: int = Field(default=12, ge=1, le=30)
    competitor_handles: list[str] = Field(default_factory=list)


class ScriptUpdateRequest(BaseModel):
    status: ScriptStatus | None = None
    scheduled_for: date | None = None


class LinkPostToScriptRequest(BaseModel):
    script_id: UUID
