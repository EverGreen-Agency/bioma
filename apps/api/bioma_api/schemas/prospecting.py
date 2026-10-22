from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ==========================================
# Sales Knowledge Cards & Playbooks Schemas
# ==========================================

class SalesKnowledgeCardResponse(BaseModel):
    id: UUID
    workspace_id: UUID | None = None
    code: str
    slug: str
    title: str
    card_type: str
    motion: str
    stage: str
    status: str
    confidence: float
    channels: list[str] = Field(default_factory=list)
    audience: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    trigger: str | None = None
    interpretation: str | None = None
    objective: str | None = None
    ask_first: str | None = None
    call_talk_track: str | None = None
    whatsapp_talk_track: str | None = None
    email_talk_track: str | None = None
    branches: list[dict[str, Any]] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    version: str = "0.1"
    created_at: datetime
    updated_at: datetime


class SalesKnowledgeCardStatusUpdate(BaseModel):
    status: Literal["HYPOTHESIS", "TESTING", "VALIDATED", "DEPRECATED"]


# ==========================================
# Prospecting Lists & Items Schemas
# ==========================================

class ProspectingItemCreate(BaseModel):
    company_name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    instagram: str | None = None
    linkedin: str | None = None
    address: str | None = None
    rating: float | None = None
    reviews_count: int = 0
    presence_score: int = 0
    category: str | None = None
    external_place_id: str | None = None


class CreateProspectingListRequest(BaseModel):
    title: str
    source: str = "local_radar"
    segment: str | None = None
    target_region: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    items: list[ProspectingItemCreate] = Field(default_factory=list)


class ProspectingListItemResponse(BaseModel):
    id: UUID
    list_id: UUID
    company_name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    instagram: str | None = None
    linkedin: str | None = None
    address: str | None = None
    rating: float | None = None
    reviews_count: int = 0
    presence_score: int = 0
    category: str | None = None
    external_place_id: str | None = None
    crm_lead_id: UUID | None = None
    ownership_warning: dict[str, Any] | None = None
    attempts_count: int = 0
    last_disposition: str | None = None
    last_attempt_at: datetime | None = None
    status: str
    notes: str | None = None
    created_at: datetime


class ProspectingListSummaryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    source: str
    segment: str | None = None
    target_region: str | None = None
    total_leads: int
    created_at: datetime


class ProspectingListDetailResponse(ProspectingListSummaryResponse):
    filters: dict[str, Any] = Field(default_factory=dict)
    items: list[ProspectingListItemResponse] = Field(default_factory=list)


# ==========================================
# Prospecting Sessions Schemas
# ==========================================

class StartProspectingSessionRequest(BaseModel):
    list_id: UUID | None = None
    motion: str = "growth"
    target_calls: int = 30


class HandoffPayload(BaseModel):
    problem: str
    impact: str
    motion: str = "growth"
    meeting_at: str
    closer_notes: str | None = None


class RecordDispositionRequest(BaseModel):
    item_id: UUID
    disposition: Literal[
        "unanswered",
        "busy",
        "wrong_number",
        "not_interested",
        "follow_up",
        "meeting_scheduled",
    ]
    notes: str | None = None
    scheduled_follow_up_at: datetime | None = None
    handoff: HandoffPayload | None = None


class ProspectingSessionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    list_id: UUID | None = None
    user_id: UUID
    motion: str
    target_calls: int
    completed_calls: int
    connections_count: int
    conversations_count: int
    meetings_booked: int
    follow_ups_count: int
    duration_seconds: int
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    items: list[ProspectingListItemResponse] = Field(default_factory=list)


class ProspectingCockpitContextResponse(BaseModel):
    session: ProspectingSessionResponse
    current_item: ProspectingListItemResponse | None = None
    queue_remaining: int
    cards: list[SalesKnowledgeCardResponse] = Field(default_factory=list)
