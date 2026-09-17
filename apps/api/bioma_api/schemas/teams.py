from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


TenantRole = Literal["tenant_admin", "operator", "approver", "viewer"]
TeamRole = Literal["manager", "member"]
WorkspaceAssignmentRole = Literal["workspace_manager", "operator", "approver", "viewer"]


class TeamCreateRequest(BaseModel):
    tenant_organization_id: UUID
    name: str = Field(min_length=1, max_length=120)


class TeamSummary(BaseModel):
    id: UUID
    tenant_organization_id: UUID
    name: str
    slug: str
    status: Literal["active", "archived"]
    members_total: int = 0
    workspaces_total: int = 0


class TeamMemberUpsertRequest(BaseModel):
    user_id: UUID
    role: TeamRole = "member"


class TeamMemberSummary(BaseModel):
    team_id: UUID
    user_id: UUID
    email: str
    display_name: str
    role: TeamRole


class TenantMembershipUpsertRequest(BaseModel):
    user_id: UUID
    role: TenantRole


class OrganizationPerson(BaseModel):
    """Alguem que pertence a organizacao — a lista de "gerenciamento de
    usuarios". Vem de `memberships`, entao quem foi convidado aparece mesmo sem
    papel de tenant."""

    user_id: UUID
    email: str
    display_name: str
    is_active: bool
    # Papel de plataforma. Hoje so `eg_admin` e `client_user` existem — todo
    # convite ao time cria admin, o que e o limite conhecido do modelo.
    role: str
    tenant_role: str | None = None
    teams: list[str] = Field(default_factory=list)


class TenantMembershipSummary(BaseModel):
    tenant_organization_id: UUID
    user_id: UUID
    email: str
    display_name: str
    role: TenantRole


class WorkspaceAssignmentUpsertRequest(BaseModel):
    user_id: UUID | None = None
    team_id: UUID | None = None
    role: WorkspaceAssignmentRole


class WorkspaceAssignmentSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID | None = None
    team_id: UUID | None = None
    assignee_name: str
    assignee_email: str | None = None
    role: WorkspaceAssignmentRole
