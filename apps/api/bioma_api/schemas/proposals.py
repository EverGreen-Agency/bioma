from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, field_validator

from bioma_api.proposal_catalog import (
    DELIVERY_MODALITY_KEYS,
    PROPOSAL_TYPE_KEYS,
    SERVICE_KEYS,
    URGENCY_KEYS,
)

OpportunityStatus = Literal[
    "new", "qualifying", "qualified", "contacted", "meeting", "proposal",
    "proposal_generated", "negotiating", "won", "lost", "rejected", "archived",
]
ProposalStatus = Literal["draft", "approved", "sent", "negotiating", "won", "lost"]
PlatformStatus = Literal["active", "paused", "not_configured"]
GenerationMode = Literal["live", "preview", "manual"]

class OpportunityBase(BaseModel):
    workspace_id: UUID | None = None
    owner_user_id: UUID | None = None
    source_platform: str = Field(min_length=2, max_length=50)
    external_id: str | None = None
    title: str = Field(min_length=2, max_length=255)
    url: str | None = None
    description: str | None = Field(default=None, max_length=10_000)
    budget_text: str | None = Field(default=None, max_length=100)
    # Nulo = ninguém avaliou ainda. Diferente de 0, que seria "avaliada e péssima".
    fit_score: int | None = Field(default=None, ge=0, le=100)
    fit_analysis: str | None = None
    status: OpportunityStatus = "new"
    next_action_at: datetime | None = None
    closed_at: datetime | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)

class OpportunityCreatePayload(OpportunityBase):
    pass

class OpportunityIngestPayload(BaseModel):
    workspace_id: UUID | None = None
    owner_user_id: UUID | None = None
    source_platform: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=255)
    url: str | None = None
    description: str | None = Field(default=None, max_length=10_000)
    budget_text: str | None = Field(default=None, max_length=100)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class OpportunityUpdatePayload(BaseModel):
    workspace_id: UUID | None = None
    owner_user_id: UUID | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    budget_text: str | None = Field(default=None, max_length=100)
    status: OpportunityStatus | None = None
    next_action_at: datetime | None = None


class CommercialActivityCreate(BaseModel):
    activity_type: Literal[
        "captured", "status_changed", "note", "follow_up_prepared", "follow_up_sent",
        "message_received", "meeting_scheduled", "meeting_completed", "proposal_created",
        "proposal_sent", "decision", "won", "lost",
    ]
    direction: Literal["internal", "inbound", "outbound"] = "internal"
    channel: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=2, max_length=500)
    body: str | None = Field(default=None, max_length=20_000)
    occurred_at: datetime | None = None
    source_kind: str = Field(default="manual", min_length=2, max_length=80)
    source_ref: str | None = Field(default=None, max_length=2_000)
    idempotency_key: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommercialActivity(CommercialActivityCreate):
    id: UUID
    opportunity_id: UUID
    occurred_at: datetime
    created_by: UUID | None = None
    created_at: datetime


class OpportunityContactCreate(BaseModel):
    lead_id: UUID
    relationship_role: Literal["contact", "champion", "decision_maker", "influencer", "billing"] = "contact"
    is_primary: bool = False


class OpportunityContact(OpportunityContactCreate):
    opportunity_id: UUID
    created_by: UUID | None = None
    created_at: datetime


class OpportunitySummary(OpportunityBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class OpportunityDetail(BaseModel):
    opportunity: OpportunitySummary
    activities: list[CommercialActivity] = Field(default_factory=list)
    contacts: list[OpportunityContact] = Field(default_factory=list)

class ProposalBase(BaseModel):
    opportunity_id: UUID | None = None
    workspace_id: UUID | None = None
    series_id: UUID | None = None
    version: int = Field(default=1, ge=1)
    # Idioma em que o CONTEÚDO nasceu — não o idioma da interface. Uma proposta
    # para lead americano nasce em 'en-US'; esse é o que sai no link público. A
    # equipe interna traduz sob demanda (ver ProposalTranslation), sem duplicar
    # o material.
    content_language: str = Field(default="pt-BR", max_length=10)
    title: str | None = Field(default=None, min_length=2, max_length=255)
    client_name: str
    target_niche: str | None = None
    executive_summary: str
    scope_offer: str | None = None
    scope_conversion: str | None = None
    scope_demand: str | None = None
    scope_items: list[dict[str, Any]] = Field(default_factory=list)
    attached_cases: list[dict[str, Any]] = Field(default_factory=list)
    win_loss_feedback: str | None = Field(default=None, max_length=5_000)
    pricing_cents: int = Field(default=0, ge=0)
    delivery_days: int = Field(default=0, ge=0, le=730)
    status: ProposalStatus = "draft"
    generation_mode: GenerationMode = "manual"
    proposal_type: str | None = None
    contractor_name: str | None = None
    team_members: list[str] = Field(default_factory=list)
    delivery_modality: str | None = None
    selected_services: list[str] = Field(default_factory=list)
    special_requirements: str | None = None
    estimated_budget: str | None = None
    payment_terms: str | None = None
    urgency: str | None = None
    decision_maker: str | None = None
    problem_summary: str | None = None
    additional_context: str | None = None
    intake_snapshot: dict[str, Any] = Field(default_factory=dict)

class ProposalCreatePayload(ProposalBase):
    pass

class ProposalUpdatePayload(BaseModel):
    content_language: str | None = Field(default=None, max_length=10)
    title: str | None = Field(default=None, min_length=2, max_length=255)
    client_name: str | None = None
    target_niche: str | None = None
    executive_summary: str | None = None
    scope_offer: str | None = None
    scope_conversion: str | None = None
    scope_demand: str | None = None
    scope_items: list[dict[str, Any]] | None = None
    win_loss_feedback: str | None = Field(default=None, max_length=5_000)
    pricing_cents: int | None = Field(default=None, ge=0)
    delivery_days: int | None = Field(default=None, ge=0, le=730)
    status: ProposalStatus | None = None
    contractor_name: str | None = Field(default=None, max_length=255)
    team_members: list[str] | None = None
    special_requirements: str | None = Field(default=None, max_length=2_000)
    estimated_budget: str | None = Field(default=None, max_length=255)
    payment_terms: str | None = Field(default=None, max_length=1_000)
    urgency: str | None = None
    decision_maker: str | None = Field(default=None, max_length=500)
    problem_summary: str | None = Field(default=None, max_length=4_000)
    additional_context: str | None = Field(default=None, max_length=4_000)


class ProposalBriefCreatePayload(BaseModel):
    workspace_id: UUID
    title: str = Field(min_length=2, max_length=255)
    proposal_type: str
    contractor_name: str = Field(min_length=2, max_length=255)
    team_members: list[str] = Field(default_factory=list, max_length=30)
    delivery_modality: str
    selected_services: list[str] = Field(min_length=1, max_length=30)
    special_requirements: str | None = Field(default=None, max_length=2_000)
    estimated_budget: str = Field(min_length=1, max_length=255)
    payment_terms: str = Field(min_length=2, max_length=1_000)
    urgency: str
    decision_maker: str = Field(min_length=2, max_length=500)
    problem_summary: str = Field(min_length=10, max_length=4_000)
    additional_context: str | None = Field(default=None, max_length=4_000)

    @field_validator("proposal_type")
    @classmethod
    def validate_proposal_type(cls, value: str) -> str:
        if value not in PROPOSAL_TYPE_KEYS:
            raise ValueError("Tipo de proposta inválido.")
        return value

    @field_validator("delivery_modality")
    @classmethod
    def validate_delivery_modality(cls, value: str) -> str:
        if value not in DELIVERY_MODALITY_KEYS:
            raise ValueError("Modalidade de entrega inválida.")
        return value

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, value: str) -> str:
        if value not in URGENCY_KEYS:
            raise ValueError("Urgência inválida.")
        return value

    @field_validator("selected_services")
    @classmethod
    def validate_services(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(value))
        invalid = sorted(set(normalized) - SERVICE_KEYS)
        if invalid:
            raise ValueError(f"Serviços inválidos: {', '.join(invalid)}")
        return normalized

class ProposalSummary(ProposalBase):
    id: UUID
    public_token: str
    public_expires_at: datetime
    created_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    # Documento renderizado — o que a tela e a tradução realmente mostram.
    content_markdown: str | None = None


class ProposalTranslateRequest(BaseModel):
    language: str = Field(min_length=2, max_length=10)


class ProposalTranslation(BaseModel):
    """Tradução em cache. `generation_mode` é sempre 'live' aqui — tradução
    nunca aceita prévia local (ver bioma_worker/translation.py)."""
    id: UUID
    proposal_id: UUID
    language: str
    title: str
    content_markdown: str
    generation_mode: Literal["live"]
    provider: str | None
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_cents: int | None
    created_by: UUID | None
    created_at: datetime


class PublicProposalResponse(BaseModel):
    client_name: str
    target_niche: str | None = None
    executive_summary: str
    scope_offer: str | None = None
    scope_conversion: str | None = None
    scope_demand: str | None = None
    scope_items: list[dict[str, Any]]
    pricing_cents: int
    delivery_days: int
    created_at: datetime


class OpportunityPlatformUpdate(BaseModel):
    platform_name: str = Field(min_length=2, max_length=100)
    status: PlatformStatus = "active"
    rss_url: HttpUrl | None = None
    monthly_cost_cents: int = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=2_000)


class OpportunityPlatformSummary(BaseModel):
    id: UUID
    platform_key: str
    platform_name: str
    status: PlatformStatus
    rss_url: str | None = None
    monthly_cost_cents: int
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class FreelancerProfileSyncRequest(BaseModel):
    profile_url: HttpUrl
    platform_key: str | None = Field(default=None, min_length=2, max_length=50)
