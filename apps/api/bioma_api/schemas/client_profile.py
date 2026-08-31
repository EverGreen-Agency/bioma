from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ClientProfilePayload(BaseModel):
    sector: str | None = Field(default=None, max_length=200)
    primary_offer: str | None = Field(default=None, max_length=500)
    initial_objective: str | None = Field(default=None, max_length=2_000)
    contact_email: str | None = Field(default=None, max_length=320)
    contact_phone: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=500)
    business_address: str | None = Field(default=None, max_length=1_000)
    business_details: str | None = Field(default=None, max_length=5_000)
    target_audience: str | None = Field(default=None, max_length=5_000)
    competitors: str | None = Field(default=None, max_length=5_000)
    marketing_objectives: str | None = Field(default=None, max_length=5_000)
    marketing_history: str | None = Field(default=None, max_length=5_000)
    challenges_opportunities: str | None = Field(default=None, max_length=5_000)
    resources_budget: str | None = Field(default=None, max_length=5_000)
    tone_of_voice: str | None = Field(default=None, max_length=2_000)
    preferences_restrictions: str | None = Field(default=None, max_length=5_000)


class ClientProfileSectionProgress(BaseModel):
    key: str
    label: str
    filled: int
    total: int
    percentage: int


class ClientProfileSummary(ClientProfilePayload):
    workspace_id: UUID
    completion_percentage: int
    sections: list[ClientProfileSectionProgress]
    updated_at: datetime | None = None
