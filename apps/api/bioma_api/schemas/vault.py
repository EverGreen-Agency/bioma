from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


VaultStatus = Literal["active", "expired", "rotating", "compromised", "revoked"]
VaultVisibility = Literal["internal", "client"]
VaultSecretField = Literal["username", "email", "password", "other_access", "token", "recovery_codes", "notes"]


class VaultSecrets(BaseModel):
    username: str | None = Field(default=None, max_length=10_000)
    email: str | None = Field(default=None, max_length=10_000)
    password: str | None = Field(default=None, max_length=10_000)
    other_access: str | None = Field(default=None, max_length=30_000)
    token: str | None = Field(default=None, max_length=30_000)
    recovery_codes: str | None = Field(default=None, max_length=30_000)
    notes: str | None = Field(default=None, max_length=30_000)

    @model_validator(mode="after")
    def require_at_least_one_secret(self):
        if not any((self.username, self.email, self.password, self.other_access, self.token, self.recovery_codes, self.notes)):
            raise ValueError("Informe pelo menos um dado de acesso.")
        return self


class VaultCredentialCreate(BaseModel):
    platform: str = Field(min_length=2, max_length=80)
    label: str = Field(min_length=2, max_length=200)
    account_hint: str | None = Field(default=None, max_length=200)
    platform_url: str | None = Field(default=None, max_length=2_000)
    visibility: VaultVisibility = "internal"
    expires_at: datetime | None = None
    owner_user_id: UUID | None = None
    secrets: VaultSecrets

    @field_validator("platform_url")
    @classmethod
    def valid_platform_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if not normalized.startswith(("https://", "http://")):
            raise ValueError("O link da plataforma deve começar com http:// ou https://.")
        return normalized


class VaultCredentialUpdate(BaseModel):
    platform: str | None = Field(default=None, min_length=2, max_length=80)
    label: str | None = Field(default=None, min_length=2, max_length=200)
    account_hint: str | None = Field(default=None, max_length=200)
    platform_url: str | None = Field(default=None, max_length=2_000)
    visibility: VaultVisibility | None = None
    expires_at: datetime | None = None
    owner_user_id: UUID | None = None
    secrets: VaultSecrets | None = None

    @field_validator("platform_url")
    @classmethod
    def valid_platform_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if not normalized.startswith(("https://", "http://")):
            raise ValueError("O link da plataforma deve começar com http:// ou https://.")
        return normalized


class VaultStatusUpdate(BaseModel):
    status: VaultStatus


class VaultReasonRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class VaultCopyRequest(VaultReasonRequest):
    field: VaultSecretField


class VaultCredentialSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    platform: str
    label: str
    account_hint: str | None = None
    platform_url: str | None = None
    visibility: VaultVisibility
    status: VaultStatus
    expires_at: datetime | None = None
    owner_user_id: UUID | None = None
    owner_name: str | None = None
    version: int
    last_rotated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VaultRevealResponse(BaseModel):
    credential_id: UUID
    secrets: VaultSecrets
    expires_in_seconds: int = 60


class VaultCopyResponse(BaseModel):
    credential_id: UUID
    field: VaultSecretField
    value: str
    expires_in_seconds: int = 60
