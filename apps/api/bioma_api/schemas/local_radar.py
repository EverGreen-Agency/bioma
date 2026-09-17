from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ProspectReviewStatus = Literal["new", "audited", "approved", "rejected", "sent"]


class LocalRadarScanCreate(BaseModel):
    niche: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    limit: int = Field(default=20, ge=1, le=60)


class LocalRadarImportRow(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=1000)
    google_maps_url: str | None = Field(default=None, max_length=1000)
    rating: float | None = Field(default=None, ge=0, le=5)
    rating_count: int | None = Field(default=None, ge=0)


class LocalRadarImportRequest(BaseModel):
    niche: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    rows: list[LocalRadarImportRow] = Field(min_length=1, max_length=500)


class LocalRadarScanSummary(BaseModel):
    id: UUID
    created_by: UUID | None = None
    niche: str
    city: str
    query_text: str
    status: Literal["completed", "failed"]
    source: Literal["places", "import"] = "places"
    error_message: str | None = None
    prospect_count: int
    created_at: datetime


class LocalRadarProspect(BaseModel):
    id: UUID
    scan_id: UUID
    place_id: str
    name: str
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    google_maps_url: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    business_status: str | None = None
    place_types: list[str] = []
    presence_score: int | None = None
    presence_gaps: list[str] = []
    changes: list[str] = []
    audit: dict[str, Any] | None = None
    audit_mode: Literal["live", "preview"] | None = None
    outreach_message: str | None = None
    review_status: ProspectReviewStatus
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    lead_id: UUID | None = None
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LocalRadarScanDetail(LocalRadarScanSummary):
    prospects: list[LocalRadarProspect] = []


class ProspectMessagePayload(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ProspectDecisionPayload(BaseModel):
    decision: Literal["approved", "rejected"]


class ProspectSendPayload(BaseModel):
    provider_type: Literal["evolution", "meta_cloud", "zapi", "custom"]


class ProspectSendResult(BaseModel):
    prospect: LocalRadarProspect
    send_status: Literal["sent", "simulated", "failed"]
    detail: str | None = None
