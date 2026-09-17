from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.teams import (
    OrganizationPerson,
    TeamCreateRequest,
    TeamMemberSummary,
    TeamMemberUpsertRequest,
    TeamSummary,
    TenantMembershipSummary,
    TenantMembershipUpsertRequest,
    WorkspaceAssignmentSummary,
    WorkspaceAssignmentUpsertRequest,
)
from bioma_api.services import teams as teams_service

router = APIRouter(tags=["teams"])


@router.get("/teams", response_model=list[TeamSummary])
def list_teams(
    tenant_organization_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[TeamSummary]:
    return teams_service.list_teams(tenant_organization_id, user)


@router.post("/teams", response_model=TeamSummary, status_code=201)
def create_team(
    payload: TeamCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> TeamSummary:
    return teams_service.create_team(payload, user)


@router.get("/teams/{team_id}/members", response_model=list[TeamMemberSummary])
def list_team_members(
    team_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[TeamMemberSummary]:
    return teams_service.list_team_members(team_id, user)


@router.put("/teams/{team_id}/members", response_model=list[TeamMemberSummary])
def upsert_team_member(
    team_id: UUID,
    payload: TeamMemberUpsertRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[TeamMemberSummary]:
    return teams_service.upsert_team_member(team_id, payload, user)


@router.delete("/teams/{team_id}/members/{user_id}", response_model=list[TeamMemberSummary])
def delete_team_member(
    team_id: UUID,
    user_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[TeamMemberSummary]:
    return teams_service.delete_team_member(team_id, user_id, user)


@router.get("/tenants/{tenant_id}/members", response_model=list[TenantMembershipSummary])
def list_tenant_memberships(
    tenant_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[TenantMembershipSummary]:
    return teams_service.list_tenant_memberships(tenant_id, user)


@router.put("/tenants/{tenant_id}/members", response_model=list[TenantMembershipSummary])
def upsert_tenant_membership(
    tenant_id: UUID,
    payload: TenantMembershipUpsertRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[TenantMembershipSummary]:
    return teams_service.upsert_tenant_membership(tenant_id, payload, user)


@router.get("/workspaces/{workspace_id}/assignments", response_model=list[WorkspaceAssignmentSummary])
def list_workspace_assignments(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkspaceAssignmentSummary]:
    return teams_service.list_workspace_assignments(workspace_id, user)


@router.put("/workspaces/{workspace_id}/assignments", response_model=list[WorkspaceAssignmentSummary])
def upsert_workspace_assignment(
    workspace_id: UUID,
    payload: WorkspaceAssignmentUpsertRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkspaceAssignmentSummary]:
    return teams_service.upsert_workspace_assignment(workspace_id, payload, user)


@router.delete(
    "/workspaces/{workspace_id}/assignments/{assignment_id}",
    response_model=list[WorkspaceAssignmentSummary],
)
def delete_workspace_assignment(
    workspace_id: UUID,
    assignment_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkspaceAssignmentSummary]:
    return teams_service.delete_workspace_assignment(workspace_id, assignment_id, user)


@router.get("/tenants/{tenant_organization_id}/people", response_model=list[OrganizationPerson])
def list_organization_people(
    tenant_organization_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[OrganizationPerson]:
    """Gerenciamento de usuarios: quem pertence a organizacao, com papel e equipes."""
    return teams_service.list_organization_people(tenant_organization_id, user)
