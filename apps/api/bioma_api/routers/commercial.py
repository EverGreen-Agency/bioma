from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.commercial import (
    ActionPlanCreateRequest,
    ActionPlanStatusUpdateRequest,
    CommercialPortalResponse,
    DiagnosticAnswerRequest,
)
from bioma_api.services import commercial as commercial_service

router = APIRouter(prefix="/workspaces", tags=["commercial"])


@router.get("/{workspace_id}/commercial", response_model=CommercialPortalResponse)
def get_commercial_portal(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return commercial_service.get_commercial_portal(workspace_id, user)


@router.post("/{workspace_id}/commercial/diagnostic", response_model=CommercialPortalResponse)
def answer_diagnostic_question(
    workspace_id: UUID,
    payload: DiagnosticAnswerRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return commercial_service.answer_diagnostic_question(workspace_id, payload, user)


@router.post("/{workspace_id}/commercial/action-plans", response_model=CommercialPortalResponse)
def create_action_plan(
    workspace_id: UUID,
    payload: ActionPlanCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return commercial_service.create_action_plan(workspace_id, payload, user)


@router.patch("/{workspace_id}/commercial/action-plans/{plan_id}", response_model=CommercialPortalResponse)
def update_action_plan_status(
    workspace_id: UUID,
    plan_id: UUID,
    payload: ActionPlanStatusUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return commercial_service.update_action_plan_status(workspace_id, plan_id, payload, user)
