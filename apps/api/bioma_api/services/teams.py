import re
import unicodedata
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import teams as teams_repo
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


def list_teams(tenant_organization_id: UUID, user: CurrentUserResponse) -> list[TeamSummary]:
    with connect() as conn:
        _require_tenant_manager(conn, tenant_organization_id, user)
        rows = teams_repo.list_teams(conn, tenant_organization_id)
    return [TeamSummary(**row) for row in rows]


def create_team(payload: TeamCreateRequest, user: CurrentUserResponse) -> TeamSummary:
    name = payload.name.strip()
    with connect() as conn:
        _require_tenant_manager(conn, payload.tenant_organization_id, user)
        base_slug = _slugify(name)
        slug = teams_repo.unique_team_slug(conn, payload.tenant_organization_id, base_slug)
        row = teams_repo.create_team(conn, payload.tenant_organization_id, name, slug)
    return TeamSummary(**row)


def list_team_members(team_id: UUID, user: CurrentUserResponse) -> list[TeamMemberSummary]:
    with connect() as conn:
        team = _managed_team(conn, team_id, user)
        rows = teams_repo.list_team_members(conn, team["id"])
    return [TeamMemberSummary(**row) for row in rows]


def upsert_team_member(
    team_id: UUID,
    payload: TeamMemberUpsertRequest,
    user: CurrentUserResponse,
) -> list[TeamMemberSummary]:
    with connect() as conn:
        team = _managed_team(conn, team_id, user)
        teams_repo.upsert_team_member(conn, team["id"], payload.user_id, payload.role)
        rows = teams_repo.list_team_members(conn, team["id"])
    return [TeamMemberSummary(**row) for row in rows]


def delete_team_member(team_id: UUID, user_id: UUID, user: CurrentUserResponse) -> list[TeamMemberSummary]:
    with connect() as conn:
        team = _managed_team(conn, team_id, user)
        teams_repo.delete_team_member(conn, team["id"], user_id)
        rows = teams_repo.list_team_members(conn, team["id"])
    return [TeamMemberSummary(**row) for row in rows]


def list_organization_people(tenant_organization_id: UUID, user: CurrentUserResponse) -> list[OrganizationPerson]:
    """Quem e da EG. Parte de `memberships` e nao de `tenant_memberships`:
    listar pelo segundo faz alguem recem-convidado sumir da tela."""
    if not is_platform_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas EG admin pode listar a equipe.")
    with connect() as conn:
        rows = teams_repo.list_organization_people(conn, tenant_organization_id)
    return [OrganizationPerson(**row) for row in rows]


def list_tenant_memberships(
    tenant_organization_id: UUID,
    user: CurrentUserResponse,
) -> list[TenantMembershipSummary]:
    with connect() as conn:
        _require_tenant_manager(conn, tenant_organization_id, user)
        rows = teams_repo.list_tenant_memberships(conn, tenant_organization_id)
    return [TenantMembershipSummary(**row) for row in rows]


def upsert_tenant_membership(
    tenant_organization_id: UUID,
    payload: TenantMembershipUpsertRequest,
    user: CurrentUserResponse,
) -> list[TenantMembershipSummary]:
    with connect() as conn:
        _require_tenant_manager(conn, tenant_organization_id, user)
        teams_repo.upsert_tenant_membership(conn, tenant_organization_id, payload.user_id, payload.role)
        rows = teams_repo.list_tenant_memberships(conn, tenant_organization_id)
    return [TenantMembershipSummary(**row) for row in rows]


def list_workspace_assignments(
    workspace_id: UUID,
    user: CurrentUserResponse,
) -> list[WorkspaceAssignmentSummary]:
    with connect() as conn:
        workspace = _managed_workspace(conn, workspace_id, user)
        rows = teams_repo.list_workspace_assignments(conn, workspace["id"])
    return [WorkspaceAssignmentSummary(**row) for row in rows]


def upsert_workspace_assignment(
    workspace_id: UUID,
    payload: WorkspaceAssignmentUpsertRequest,
    user: CurrentUserResponse,
) -> list[WorkspaceAssignmentSummary]:
    if (payload.user_id is None) == (payload.team_id is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe exatamente um usuário ou um time.",
        )
    with connect() as conn:
        workspace = _managed_workspace(conn, workspace_id, user)
        if payload.team_id:
            team = teams_repo.find_team(conn, payload.team_id)
            if not team or team["tenant_organization_id"] != workspace["tenant_organization_id"]:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Time inválido para o tenant.")
        teams_repo.upsert_workspace_assignment(
            conn,
            workspace["id"],
            payload.user_id,
            payload.team_id,
            payload.role,
            user.id,
        )
        rows = teams_repo.list_workspace_assignments(conn, workspace["id"])
    return [WorkspaceAssignmentSummary(**row) for row in rows]


def delete_workspace_assignment(
    workspace_id: UUID,
    assignment_id: UUID,
    user: CurrentUserResponse,
) -> list[WorkspaceAssignmentSummary]:
    with connect() as conn:
        workspace = _managed_workspace(conn, workspace_id, user)
        teams_repo.delete_workspace_assignment(conn, workspace["id"], assignment_id)
        rows = teams_repo.list_workspace_assignments(conn, workspace["id"])
    return [WorkspaceAssignmentSummary(**row) for row in rows]


def _managed_team(conn, team_id: UUID, user: CurrentUserResponse):
    team = teams_repo.find_team(conn, team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time não encontrado.")
    _require_tenant_manager(conn, team["tenant_organization_id"], user)
    return team


def _managed_workspace(conn, workspace_id: UUID, user: CurrentUserResponse):
    workspace = teams_repo.find_workspace(conn, workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    _require_tenant_manager(conn, workspace["tenant_organization_id"], user)
    return workspace


def _require_tenant_manager(conn, tenant_organization_id: UUID, user: CurrentUserResponse) -> None:
    if is_platform_admin(user) or teams_repo.can_manage_tenant(conn, tenant_organization_id, user.id):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado.")


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "time"
