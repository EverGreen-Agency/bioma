from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.squads import (
    FinOpsSummaryResponse,
    RunSquadPayload,
    SquadDefinitionPayload,
    SquadDefinitionSummary,
    SquadExecutionSummary,
)
from bioma_api.services import squads as squads_service

router = APIRouter(prefix="/workspaces/{workspace_id}/squads", tags=["autonomous-squads"])


@router.get("", response_model=list[SquadDefinitionSummary])
def list_squads(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SquadDefinitionSummary]:
    return squads_service.list_squads(workspace_id, user)


@router.post("", response_model=SquadDefinitionSummary)
def upsert_squad(
    workspace_id: UUID,
    payload: SquadDefinitionPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> SquadDefinitionSummary:
    return squads_service.upsert_squad(workspace_id, payload, user)


@router.post("/run", response_model=SquadExecutionSummary, status_code=status.HTTP_201_CREATED)
def run_squad(
    workspace_id: UUID,
    payload: RunSquadPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> SquadExecutionSummary:
    return squads_service.run_squad(workspace_id, payload, user)


@router.get("/executions", response_model=list[SquadExecutionSummary])
def list_executions(
    workspace_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SquadExecutionSummary]:
    return squads_service.list_executions(workspace_id, user, limit)


@router.get("/finops", response_model=FinOpsSummaryResponse)
def get_finops(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> FinOpsSummaryResponse:
    return squads_service.get_finops(workspace_id, user)
