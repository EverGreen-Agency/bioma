from uuid import UUID

from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.improvement_requests import (
    ImprovementRequest,
    ImprovementRequestConvert,
    ImprovementRequestCreate,
    ImprovementRequestReject,
)
from bioma_api.services import improvement_requests as service

router = APIRouter(prefix="/improvement-requests", tags=["improvement-requests"])


@router.get("", response_model=list[ImprovementRequest])
def list_requests(
    status: str | None = Query(default=None),
    workspace_id: UUID | None = Query(default=None),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[ImprovementRequest]:
    return service.list_requests(status, workspace_id, user)


@router.post("", response_model=ImprovementRequest, status_code=201)
def create_request(
    payload: ImprovementRequestCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ImprovementRequest:
    return service.create_request(payload, user)


@router.post("/{request_id}/convert", response_model=ImprovementRequest)
def convert_to_task(
    request_id: UUID,
    payload: ImprovementRequestConvert,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ImprovementRequest:
    """Vira tarefa de verdade — com prazo e dono — e sai da fila."""
    return service.convert_to_task(request_id, payload, user)


@router.post("/{request_id}/reject", response_model=ImprovementRequest)
def reject_request(
    request_id: UUID,
    payload: ImprovementRequestReject,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ImprovementRequest:
    return service.reject_request(request_id, payload, user)
