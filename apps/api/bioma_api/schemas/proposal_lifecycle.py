from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from bioma_api.schemas.proposals import ProposalStatus, ProposalSummary


ClaimsReviewStatus = Literal["pending", "approved", "rejected"]
AcceptanceStatus = Literal["not_requested", "pending", "accepted", "rejected"]
DeliveryChannel = Literal["share_link", "manual_email", "signature_adapter"]


class ProposalClaim(BaseModel):
    text: str = Field(min_length=2, max_length=1_000)
    evidence_ref: str | None = Field(default=None, max_length=2_000)
    approved: bool = False


class ProposalLifecycleRecord(ProposalSummary):
    content_markdown: str = ""
    content_sections: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    claims_review_status: ClaimsReviewStatus = "pending"
    archived_at: datetime | None = None
    viewed_at: datetime | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    negotiating_at: datetime | None = None
    won_at: datetime | None = None
    lost_at: datetime | None = None
    acceptance_status: AcceptanceStatus = "not_requested"
    accepted_at: datetime | None = None
    accepted_by_name: str | None = None
    accepted_by_email: str | None = None


class PublicProposalLifecycleRecord(BaseModel):
    title: str | None = None
    client_name: str
    contractor_name: str | None = None
    version: int
    status: ProposalStatus
    content_markdown: str
    claims_review_status: ClaimsReviewStatus
    acceptance_status: AcceptanceStatus
    accepted_at: datetime | None = None
    accepted_by_name: str | None = None


class ProposalEvent(BaseModel):
    id: UUID
    proposal_id: UUID
    event_type: str
    actor_user_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ProposalDelivery(BaseModel):
    id: UUID
    proposal_id: UUID
    channel: DeliveryChannel
    recipient_name: str | None = None
    recipient_email: str | None = None
    provider: str | None = None
    external_id: str | None = None
    status: Literal["prepared", "sent", "delivered", "accepted", "rejected", "failed"]
    metadata: dict[str, Any] = Field(default_factory=dict)
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ProposalConversion(BaseModel):
    id: UUID
    proposal_id: UUID
    idempotency_key: str
    project_id: UUID
    contract_id: UUID
    plan_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime


class ProposalDetailResponse(BaseModel):
    proposal: ProposalLifecycleRecord
    revisions: list[ProposalLifecycleRecord] = Field(default_factory=list)
    events: list[ProposalEvent] = Field(default_factory=list)
    deliveries: list[ProposalDelivery] = Field(default_factory=list)
    conversion: ProposalConversion | None = None


class ProposalContentUpdate(BaseModel):
    content_markdown: str = Field(min_length=20, max_length=100_000)
    claims: list[ProposalClaim] = Field(default_factory=list, max_length=100)


class ProposalClaimsReview(BaseModel):
    status: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=2_000)


class ProposalStatusTransition(BaseModel):
    status: ProposalStatus
    reason: str | None = Field(default=None, max_length=2_000)


class ProposalRevisionCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=2_000)


class ProposalDeliveryCreate(BaseModel):
    channel: DeliveryChannel
    recipient_name: str | None = Field(default=None, max_length=255)
    recipient_email: EmailStr | None = None
    provider: str | None = Field(default=None, max_length=100)
    external_id: str | None = Field(default=None, max_length=255)
    confirm_external_send: bool = False


class ProposalAcceptanceCreate(BaseModel):
    accepted: bool
    signer_name: str = Field(min_length=2, max_length=255)
    signer_email: EmailStr
    confirmation: Literal["ACEITO_OS_TERMOS_DA_PROPOSTA"]


class ProposalArchiveRequest(BaseModel):
    confirm: bool
    reason: str | None = Field(default=None, max_length=2_000)


class ProposalConversionCreate(BaseModel):
    confirm: bool
    idempotency_key: str = Field(min_length=8, max_length=255)
    project_name: str | None = Field(default=None, min_length=2, max_length=255)
    project_type: Literal["tech", "growth", "social", "general"] = "general"
    generate_plan_draft: bool = True


class ProposalCohort(BaseModel):
    month: str
    created: int
    sent: int
    won: int
    lost: int
    win_rate_percentage: float
    average_days_to_close: float | None = None


class ProposalCohortAnalytics(BaseModel):
    cohorts: list[ProposalCohort] = Field(default_factory=list)
    median_days_to_first_send: float | None = None
    median_days_to_close: float | None = None
    generated_at: datetime
