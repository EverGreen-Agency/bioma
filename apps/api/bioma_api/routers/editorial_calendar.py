from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.editorial_calendar import (
    EditorialCalendarItemPayload,
    EditorialCalendarItemSummary,
)
from bioma_api.services import editorial_calendar as cal_service

router = APIRouter(prefix="/workspaces/{workspace_id}/calendar", tags=["editorial-calendar"])


@router.get("", response_model=list[EditorialCalendarItemSummary])
def list_items(
    workspace_id: UUID,
    stage: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[EditorialCalendarItemSummary]:
    return cal_service.list_items(workspace_id, user, stage, limit)


@router.post("", response_model=EditorialCalendarItemSummary, status_code=status.HTTP_201_CREATED)
def create_item(
    workspace_id: UUID,
    payload: EditorialCalendarItemPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> EditorialCalendarItemSummary:
    return cal_service.create_item(workspace_id, payload, user)


@router.patch("/{item_id}/stage", response_model=EditorialCalendarItemSummary)
def update_stage(
    workspace_id: UUID,
    item_id: UUID,
    stage: str = Query(...),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> EditorialCalendarItemSummary:
    return cal_service.update_stage(workspace_id, item_id, stage, user)
