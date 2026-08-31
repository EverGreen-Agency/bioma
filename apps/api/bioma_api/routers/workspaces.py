from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.workspaces import (
    WorkspaceSavedViewCreateRequest,
    WorkspaceSavedViewSummary,
    WorkspaceSummary,
)
from bioma_api.services import workspaces as workspaces_service


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceSummary])
def list_workspaces(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkspaceSummary]:
    return workspaces_service.list_workspaces(user)


@router.get("/views", response_model=list[WorkspaceSavedViewSummary])
def list_saved_views(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkspaceSavedViewSummary]:
    return workspaces_service.list_saved_views(user)


@router.post("/views", response_model=WorkspaceSavedViewSummary, status_code=201)
def create_saved_view(
    payload: WorkspaceSavedViewCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkspaceSavedViewSummary:
    return workspaces_service.create_saved_view(payload, user)


@router.delete("/views/{view_id}", response_model=list[WorkspaceSavedViewSummary])
def delete_saved_view(
    view_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkspaceSavedViewSummary]:
    return workspaces_service.delete_saved_view(view_id, user)


@router.put("/{workspace_id}/favorite", response_model=list[WorkspaceSummary])
def favorite_workspace(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkspaceSummary]:
    return workspaces_service.set_favorite(workspace_id, True, user)


@router.delete("/{workspace_id}/favorite", response_model=list[WorkspaceSummary])
def unfavorite_workspace(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkspaceSummary]:
    return workspaces_service.set_favorite(workspace_id, False, user)
