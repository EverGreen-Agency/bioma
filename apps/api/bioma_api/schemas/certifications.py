from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

CertificationStatus = Literal["active", "expiring_soon", "expired"]


class CertificationCreateRequest(BaseModel):
    user_id: UUID | None = Field(default=None, description="Nulo = certificação da própria EG (ex.: Google Partner).")
    provider: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=2, max_length=240)
    credential_id: str | None = Field(default=None, max_length=200)
    verification_url: str | None = Field(default=None, max_length=1000)
    issued_at: date
    expires_at: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.expires_at and self.expires_at < self.issued_at:
            raise ValueError("A data de expiração não pode ser anterior à emissão.")
        return self


class CertificationUpdateRequest(BaseModel):
    provider: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=2, max_length=240)
    credential_id: str | None = Field(default=None, max_length=200)
    verification_url: str | None = Field(default=None, max_length=1000)
    issued_at: date | None = None
    expires_at: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CertificationSummary(BaseModel):
    id: UUID
    user_id: UUID | None = None
    holder_name: str
    provider: str
    name: str
    credential_id: str | None = None
    verification_url: str | None = None
    issued_at: date
    expires_at: date | None = None
    status: CertificationStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
