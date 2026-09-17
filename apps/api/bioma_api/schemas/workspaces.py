from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


WorkspaceKind = Literal["agency_internal", "client"]
WorkspaceStatus = Literal["active", "archived"]
WorkspaceAccessRole = Literal[
    "platform_admin",
    "tenant_admin",
    "workspace_manager",
    "operator",
    "approver",
    "viewer",
    "client_user",
]


class WorkspaceSummary(BaseModel):
    id: UUID
    tenant_organization_id: UUID
    tenant_name: str
    tenant_slug: str
    organization_id: UUID
    organization_name: str
    organization_slug: str
    kind: WorkspaceKind
    name: str
    slug: str
    status: WorkspaceStatus
    client_id: UUID | None = None
    legacy_client_id: UUID | None = None
    operational_client_id: UUID | None = None
    client_status: Literal["onboarding", "active", "paused", "completed", "archived"] | None = None
    responsible_name: str | None = None
    enabled_modules: list[str] = Field(default_factory=list)
    access_role: WorkspaceAccessRole
    is_favorite: bool = False
    is_assigned: bool = False


class WorkspaceSavedViewFilters(BaseModel):
    query: str = ""
    kinds: list[WorkspaceKind] = Field(default_factory=list)
    access_roles: list[WorkspaceAccessRole] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    favorite_only: bool = False
    mine_only: bool = False


class WorkspaceSavedViewCreateRequest(BaseModel):
    tenant_organization_id: UUID | None = None
    name: str = Field(min_length=1, max_length=80)
    filters: WorkspaceSavedViewFilters


class WorkspaceSavedViewSummary(BaseModel):
    id: UUID
    tenant_organization_id: UUID | None = None
    name: str
    filters: WorkspaceSavedViewFilters
