from uuid import UUID
from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module
from bioma_api.db import connect
from bioma_api.repositories import editorial_calendar as cal_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.editorial_calendar import (
    EditorialCalendarItemPayload,
    EditorialCalendarItemSummary,
)


def list_items(
    workspace_id: UUID,
    user: CurrentUserResponse,
    stage: str | None = None,
    limit: int = 100,
) -> list[EditorialCalendarItemSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = cal_repo.list_calendar_items(conn, client["workspace_id"], stage, limit)
    return [EditorialCalendarItemSummary(**dict(r)) for r in rows]


def create_item(
    workspace_id: UUID,
    payload: EditorialCalendarItemPayload,
    user: CurrentUserResponse,
) -> EditorialCalendarItemSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        row = cal_repo.create_calendar_item(conn, client["workspace_id"], payload.model_dump())
    return EditorialCalendarItemSummary(**dict(row))


def update_stage(
    workspace_id: UUID,
    item_id: UUID,
    stage: str,
    user: CurrentUserResponse,
) -> EditorialCalendarItemSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        row = cal_repo.update_calendar_stage(conn, client["workspace_id"], item_id, stage)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado.")
    return EditorialCalendarItemSummary(**dict(row))


def _accessible_workspace(conn, workspace_id: UUID, user: CurrentUserResponse):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "content")
    return client
