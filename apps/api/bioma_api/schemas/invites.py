from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from bioma_api.schemas.auth import CurrentUserResponse


class InviteCreateRequest(BaseModel):
    email: EmailStr | None = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class TeamInviteCreateRequest(BaseModel):
    """Convite para o time da EG. `team_id` e `tenant_role` são opcionais, mas
    preenchê-los evita o segundo passo manual — que é onde se esquece."""

    email: EmailStr | None = None
    expires_in_days: int = Field(default=7, ge=1, le=30)
    # `eg_member` e o default DE PROPOSITO: administrador tem que ser escolha
    # explicita. Ate a 0090 nao havia alternativa e todo convite criava admin.
    role: Literal["eg_member", "eg_admin"] = "eg_member"
    team_id: UUID | None = None
    tenant_role: Literal["tenant_admin", "operator", "approver", "viewer"] | None = None


class InviteCreatedResponse(BaseModel):
    id: UUID
    token: str
    path: str
    email: EmailStr | None = None
    expires_at: datetime


class InviteSummary(BaseModel):
    id: UUID
    email: EmailStr | None = None
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime
    # Nulos em convite de cliente; preenchidos no convite de time (0088).
    role: str | None = None
    team_id: UUID | None = None
    tenant_role: str | None = None


class InvitePublicResponse(BaseModel):
    # Em convite de time não existe cliente; a tela pública mostra o nome da
    # organização nos dois casos (o repositório faz o coalesce).
    client_name: str
    organization_name: str
    email: EmailStr | None = None
    expires_at: datetime
    # Deixa a tela pública dizer "você foi convidado para a equipe X" em vez de
    # tratar convite de time como se fosse de cliente.
    team_name: str | None = None


class InviteAcceptRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class InviteAcceptResponse(BaseModel):
    user: CurrentUserResponse
    expires_at: datetime
