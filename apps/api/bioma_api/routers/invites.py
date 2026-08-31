from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from bioma_api.auth import current_user_from_request, session_cookie_kwargs, user_from_session_token
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.invites import (
    InviteAcceptRequest,
    InviteAcceptResponse,
    InviteCreatedResponse,
    InviteCreateRequest,
    InvitePublicResponse,
    InviteSummary,
    TeamInviteCreateRequest,
)
from bioma_api.services import invites as invites_service


admin_router = APIRouter(prefix="/clients/{client_id}/invites", tags=["invites"])
workspace_admin_router = APIRouter(prefix="/workspaces/{client_id}/invites", tags=["workspace-invites"])
public_router = APIRouter(prefix="/auth/invites", tags=["invites"])
# Convite para o time da EG. Rota separada porque o sujeito é outro: o convite
# de cliente é por workspace de cliente, este é pelo tenant.
team_router = APIRouter(prefix="/tenants/{tenant_organization_id}/invites", tags=["team-invites"])


@admin_router.post("", response_model=InviteCreatedResponse, status_code=status.HTTP_201_CREATED)
@workspace_admin_router.post("", response_model=InviteCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    client_id: UUID,
    payload: InviteCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> InviteCreatedResponse:
    return invites_service.create_invite(client_id, payload, user)


@admin_router.get("", response_model=list[InviteSummary])
@workspace_admin_router.get("", response_model=list[InviteSummary])
def list_invites(
    client_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[InviteSummary]:
    return invites_service.list_invites(client_id, user)


@admin_router.delete("/{invite_id}", response_model=list[InviteSummary])
@workspace_admin_router.delete("/{invite_id}", response_model=list[InviteSummary])
def revoke_invite(
    client_id: UUID,
    invite_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[InviteSummary]:
    return invites_service.revoke_invite(client_id, invite_id, user)


@team_router.post("", response_model=InviteCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_team_invite(
    tenant_organization_id: UUID,
    payload: TeamInviteCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> InviteCreatedResponse:
    return invites_service.create_team_invite(tenant_organization_id, payload, user)


@team_router.get("", response_model=list[InviteSummary])
def list_team_invites(
    tenant_organization_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[InviteSummary]:
    return invites_service.list_team_invites(tenant_organization_id, user)


@team_router.delete("/{invite_id}", response_model=list[InviteSummary])
def revoke_team_invite(
    tenant_organization_id: UUID,
    invite_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[InviteSummary]:
    return invites_service.revoke_team_invite(tenant_organization_id, invite_id, user)


@public_router.get("/{token}", response_model=InvitePublicResponse)
def get_invite(token: str) -> InvitePublicResponse:
    return invites_service.get_invite_public(token)


@public_router.post("/{token}/accept", response_model=InviteAcceptResponse)
def accept_invite(token: str, payload: InviteAcceptRequest, response: Response) -> InviteAcceptResponse:
    session_token, expires_at, _user_id = invites_service.accept_invite(token, payload)
    response.set_cookie(value=session_token, **session_cookie_kwargs(expires_at))
    return InviteAcceptResponse(user=user_from_session_token(session_token), expires_at=expires_at)
