from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


SessionType = Literal["sales_call", "discovery", "proposal_review", "follow_up"]
SessionStatus = Literal["draft", "prepared", "active", "completed", "cancelled"]
CopilotEventType = Literal["transcript_chunk", "objection", "insight", "note", "action_item"]
MeetingProvider = Literal["manual", "google_meet", "microsoft_teams"]
ParticipantGroup = Literal["eg_team", "client", "partner", "unknown"]
ParticipantSeniority = Literal["individual", "manager", "director", "c_level", "owner", "unknown"]
ParticipantDecisionRole = Literal["champion", "decision_maker", "influencer", "technical", "user", "unknown"]
SuggestionType = Literal["question", "objection_response", "risk", "opportunity", "next_step"]
ActionType = Literal["follow_up_task", "proposal_revision", "project_update", "opportunity_registration"]


class SalesCopilotSessionCreate(BaseModel):
    workspace_id: UUID | None = None
    opportunity_id: UUID | None = None
    proposal_id: UUID | None = None
    title: str = Field(min_length=2, max_length=255)
    session_type: SessionType = "sales_call"
    language: str = Field(default="pt-BR", min_length=2, max_length=20)
    objective: str | None = Field(default=None, max_length=4_000)
    participant_context: str | None = Field(default=None, max_length=4_000)


class SalesCopilotEventCreate(BaseModel):
    event_type: CopilotEventType
    content: str = Field(min_length=1, max_length=20_000)
    recommendation: str | None = Field(default=None, max_length=10_000)
    source_refs: list[dict[str, Any]] = Field(default_factory=list, max_length=50)


class SalesCopilotEvent(BaseModel):
    id: UUID
    session_id: UUID
    event_type: CopilotEventType
    content: str
    recommendation: str | None = None
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    sequence: int
    created_by: UUID | None = None
    created_at: datetime


class SalesCopilotMeetingConfigure(BaseModel):
    meeting_provider: MeetingProvider = "manual"
    meeting_url: str | None = Field(default=None, max_length=2_000)
    external_meeting_id: str | None = Field(default=None, max_length=500)
    consent_granted: bool
    retention_days: int = Field(default=90, ge=1, le=365)


class SalesCopilotParticipantCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=255)
    participant_group: ParticipantGroup = "unknown"
    organization_name: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    seniority: ParticipantSeniority = "unknown"
    decision_role: ParticipantDecisionRole = "unknown"
    email: str | None = Field(default=None, max_length=320)
    external_speaker_id: str | None = Field(default=None, max_length=500)
    context_notes: str | None = Field(default=None, max_length=4_000)


class SalesCopilotParticipant(SalesCopilotParticipantCreate):
    id: UUID
    session_id: UUID
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SalesCopilotTranscriptSegmentCreate(BaseModel):
    idempotency_key: str = Field(min_length=4, max_length=255)
    participant_id: UUID | None = None
    source: Literal["manual", "upload", "google_meet", "microsoft_teams", "provider_webhook"] = "manual"
    external_speaker_id: str | None = Field(default=None, max_length=500)
    speaker_label: str | None = Field(default=None, max_length=255)
    start_ms: int = Field(default=0, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    content: str = Field(min_length=1, max_length=20_000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    is_final: bool = True


class FathomMeetingInvitee(BaseModel):
    name: str | None = None
    email: str | None = None
    domain: str | None = None


class FathomMeeting(BaseModel):
    recording_id: int
    title: str
    meeting_type: str | None = None
    url: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    recorded_by: str | None = None
    external_invitees: list[FathomMeetingInvitee] = Field(default_factory=list)


class FathomImportRequest(BaseModel):
    recording_id: int
    analyze_after_import: bool = True


class FathomImportResult(BaseModel):
    session_id: UUID
    recording_id: int
    imported_segments: int
    skipped_segments: int
    analyzed: bool


class SalesCopilotTranscriptBatch(BaseModel):
    segments: list[SalesCopilotTranscriptSegmentCreate] = Field(min_length=1, max_length=100)
    analyze_after_ingest: bool = False


class SalesCopilotIngestionCredential(BaseModel):
    session_id: UUID
    ingest_token: str
    endpoint_path: str
    expires_at: datetime | None = None


class SalesCopilotIngestionAck(BaseModel):
    session_id: UUID
    accepted_segments: int
    status: Literal["accepted"] = "accepted"


class SalesCopilotTranscriptSegment(BaseModel):
    id: UUID
    session_id: UUID
    participant_id: UUID | None = None
    idempotency_key: str
    source: str
    external_speaker_id: str | None = None
    speaker_label: str | None = None
    start_ms: int
    end_ms: int | None = None
    content: str
    confidence: float | None = None
    is_final: bool
    sequence: int
    created_by: UUID | None = None
    created_at: datetime


class SalesCopilotLiveSuggestion(BaseModel):
    id: UUID
    session_id: UUID
    suggestion_type: SuggestionType
    title: str
    content: str
    rationale: str | None = None
    confidence: float | None = None
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    generation_mode: str
    status: Literal["active", "used", "dismissed"]
    created_at: datetime


class SalesCopilotLiveAnalyzeRequest(BaseModel):
    window_segments: int = Field(default=12, ge=3, le=50)
    focus: str | None = Field(default=None, max_length=2_000)


class SalesCopilotActionCreate(BaseModel):
    action_type: ActionType
    title: str = Field(min_length=2, max_length=500)
    detail: str | None = Field(default=None, max_length=10_000)
    owner_hint: str | None = Field(default=None, max_length=255)
    due_at: datetime | None = None
    source_refs: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    idempotency_key: str | None = Field(default=None, min_length=4, max_length=255)


class SalesCopilotAction(SalesCopilotActionCreate):
    id: UUID
    session_id: UUID
    status: Literal["proposed", "approved", "materialized", "dismissed", "failed"]
    materialized_ref: dict[str, Any] = Field(default_factory=dict)
    created_by: UUID | None = None
    approved_by: UUID | None = None
    materialized_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SalesCopilotActionMaterialize(BaseModel):
    confirm: bool
    idempotency_key: str = Field(min_length=8, max_length=255)


class SalesJourneySnapshot(BaseModel):
    id: UUID
    session_id: UUID
    workspace_id: UUID | None = None
    opportunity_id: UUID | None = None
    current_funnel_stage: str
    funnel_map: list[dict[str, Any]] = Field(default_factory=list)
    journey_stages: list[dict[str, Any]] = Field(default_factory=list)
    scores: dict[str, Any] = Field(default_factory=dict)
    bottlenecks: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    generation_mode: str
    created_at: datetime
    updated_at: datetime


class SalesCopilotSession(BaseModel):
    id: UUID
    workspace_id: UUID | None = None
    opportunity_id: UUID | None = None
    proposal_id: UUID | None = None
    title: str
    session_type: SessionType
    language: str
    status: SessionStatus
    realtime_status: Literal["not_configured", "adapter_ready", "live", "failed"]
    objective: str | None = None
    participant_context: str | None = None
    meeting_provider: MeetingProvider = "manual"
    meeting_url: str | None = None
    external_meeting_id: str | None = None
    consent_status: Literal["pending", "granted", "revoked"] = "pending"
    consent_recorded_at: datetime | None = None
    retention_until: datetime | None = None
    live_context: dict[str, Any] = Field(default_factory=dict)
    knowledge_snapshot: dict[str, Any] = Field(default_factory=dict)
    preparation_brief: dict[str, Any] = Field(default_factory=dict)
    transcript: str
    summary: str | None = None
    duration_seconds: int
    created_by: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    events: list[SalesCopilotEvent] = Field(default_factory=list)
    participants: list[SalesCopilotParticipant] = Field(default_factory=list)
    segments: list[SalesCopilotTranscriptSegment] = Field(default_factory=list)
    suggestions: list[SalesCopilotLiveSuggestion] = Field(default_factory=list)
    actions: list[SalesCopilotAction] = Field(default_factory=list)
    journey_snapshot: SalesJourneySnapshot | None = None


class SalesCopilotCompleteRequest(BaseModel):
    duration_seconds: int = Field(default=0, ge=0, le=86_400)


class SalesCopilotMetrics(BaseModel):
    total_sessions: int
    total_duration_seconds: int
    analyses_completed: int
    sessions_by_status: dict[str, int] = Field(default_factory=dict)


class RealtimeAdapterStatus(BaseModel):
    available: bool
    status: Literal["not_configured", "adapter_ready"]
    message: str
    supported_input: list[str] = Field(default_factory=list)
    supported_meeting_providers: list[MeetingProvider] = Field(default_factory=list)
    transport: Literal["polling", "sse", "websocket"] = "polling"
