from bioma_api.access import is_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from fastapi import HTTPException, status

from bioma_api.schemas.workspaces import (
    WorkspaceSavedViewCreateRequest,
    WorkspaceSavedViewSummary,
    WorkspaceSummary,
)


def list_workspaces(user: CurrentUserResponse) -> list[WorkspaceSummary]:
    with connect() as conn:
        rows = workspaces_repo.list_accessible_workspaces(
            conn,
            is_platform_admin(user),
            user.id,
        )
    return [WorkspaceSummary(**row) for row in rows]


def set_favorite(workspace_id, favorite: bool, user: CurrentUserResponse) -> list[WorkspaceSummary]:
    is_admin = is_platform_admin(user)
    with connect() as conn:
        workspace = workspaces_repo.find_accessible_workspace(conn, workspace_id, is_admin, user.id)
        if not workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
        workspaces_repo.set_favorite(conn, workspace_id, user.id, favorite)
    return list_workspaces(user)


def list_saved_views(user: CurrentUserResponse) -> list[WorkspaceSavedViewSummary]:
    with connect() as conn:
        rows = workspaces_repo.list_saved_views(conn, user.id)
    return [WorkspaceSavedViewSummary(**row) for row in rows]


def create_saved_view(
    payload: WorkspaceSavedViewCreateRequest,
    user: CurrentUserResponse,
) -> WorkspaceSavedViewSummary:
    name = payload.name.strip()
    with connect() as conn:
        try:
            row = workspaces_repo.create_saved_view(
                conn,
                user.id,
                payload.tenant_organization_id,
                name,
                payload.filters.model_dump(),
            )
        except Exception as error:
            if getattr(error, "sqlstate", None) == "23505":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe uma visão com este nome.") from error
            raise
    return WorkspaceSavedViewSummary(**row)


def delete_saved_view(view_id, user: CurrentUserResponse) -> list[WorkspaceSavedViewSummary]:
    with connect() as conn:
        workspaces_repo.delete_saved_view(conn, user.id, view_id)
    return list_saved_views(user)
