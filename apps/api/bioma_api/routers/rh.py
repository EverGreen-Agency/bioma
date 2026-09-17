from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.rh import (
    ManagerPortfolioResponse,
    MilestoneCompletionRequest,
    MilestoneTemplateCreateRequest,
    MilestoneTemplateSummary,
    MilestoneTemplateUpdateRequest,
    OnboardingPlanCreateRequest,
    OnboardingPlanSummary,
    SatisfactionScoreCreateRequest,
    SatisfactionScoreSummary,
)
from bioma_api.services import rh as rh_service

router = APIRouter(prefix="/backoffice/rh", tags=["rh"])


@router.get("/onboarding/templates", response_model=list[MilestoneTemplateSummary])
def list_milestone_templates(user: CurrentUserResponse = Depends(current_user_from_request)):
    return rh_service.list_milestone_templates(user)


@router.post("/onboarding/templates", response_model=MilestoneTemplateSummary, status_code=201)
def create_milestone_template(payload: MilestoneTemplateCreateRequest, user: CurrentUserResponse = Depends(current_user_from_request)):
    return rh_service.create_milestone_template(payload, user)


@router.patch("/onboarding/templates/{template_id}", response_model=MilestoneTemplateSummary)
def update_milestone_template(
    template_id: UUID,
    payload: MilestoneTemplateUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return rh_service.update_milestone_template(template_id, payload, user)


@router.get("/onboarding/plans", response_model=list[OnboardingPlanSummary])
def list_onboarding_plans(user: CurrentUserResponse = Depends(current_user_from_request)):
    return rh_service.list_onboarding_plans(user)


@router.post("/onboarding/plans", response_model=OnboardingPlanSummary, status_code=201)
def create_onboarding_plan(payload: OnboardingPlanCreateRequest, user: CurrentUserResponse = Depends(current_user_from_request)):
    return rh_service.create_onboarding_plan(payload, user)


@router.patch("/onboarding/plans/{plan_id}/milestone", response_model=OnboardingPlanSummary)
def update_milestone_status(
    plan_id: UUID,
    payload: MilestoneCompletionRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return rh_service.update_milestone_status(plan_id, payload, user)


@router.get("/workspaces/{workspace_id}/satisfaction", response_model=list[SatisfactionScoreSummary])
def list_satisfaction_scores(workspace_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return rh_service.list_satisfaction_scores(workspace_id, user)


@router.post("/workspaces/{workspace_id}/satisfaction", response_model=SatisfactionScoreSummary, status_code=201)
def create_satisfaction_score(
    workspace_id: UUID,
    payload: SatisfactionScoreCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return rh_service.create_satisfaction_score(workspace_id, payload, user)


@router.get("/managers/{manager_user_id}/portfolio", response_model=ManagerPortfolioResponse)
def manager_portfolio(manager_user_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return rh_service.manager_portfolio(manager_user_id, user)
