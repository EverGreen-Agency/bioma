from uuid import UUID

from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.ai_operations import (
    AiFinOpsDashboard,
    AiQuotaSnapshotCreate,
    AiSubscriptionCreate,
    AiSubscriptionUpdate,
    AiUsageEventCreate,
    WorkflowDefinitionSummary,
    WorkflowRunCreate,
    WorkflowRunSummary,
    WorkflowStepComplete,
    WorkflowTemplateSummary,
)
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services import ai_operations as service


router = APIRouter(prefix="/backoffice/ai-operations", tags=["ai-operations"])


@router.get("/finops", response_model=AiFinOpsDashboard)
def get_finops(user: CurrentUserResponse = Depends(current_user_from_request)) -> AiFinOpsDashboard:
    return service.get_finops_dashboard(user)


@router.post("/subscriptions", response_model=AiFinOpsDashboard, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: AiSubscriptionCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiFinOpsDashboard:
    return service.create_subscription(payload, user)


@router.patch("/subscriptions/{subscription_id}", response_model=AiFinOpsDashboard)
def update_subscription(
    subscription_id: UUID,
    payload: AiSubscriptionUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiFinOpsDashboard:
    return service.update_subscription(subscription_id, payload, user)


@router.post("/subscriptions/{subscription_id}/quota", response_model=AiFinOpsDashboard, status_code=201)
def record_quota(
    subscription_id: UUID,
    payload: AiQuotaSnapshotCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiFinOpsDashboard:
    return service.create_quota_snapshot(subscription_id, payload, user)


@router.post("/usage", response_model=AiFinOpsDashboard, status_code=201)
def record_usage(
    payload: AiUsageEventCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiFinOpsDashboard:
    return service.record_usage(payload, user)


@router.get("/workflow-templates", response_model=list[WorkflowTemplateSummary])
def list_workflow_templates(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkflowTemplateSummary]:
    return service.list_templates(user)


@router.get("/workflow-definitions", response_model=list[WorkflowDefinitionSummary])
def list_workflow_definitions(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkflowDefinitionSummary]:
    return service.list_definitions(user)


@router.post("/workflow-templates/{slug}/install", response_model=list[WorkflowDefinitionSummary])
def install_workflow_template(
    slug: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkflowDefinitionSummary]:
    return service.install_template(slug, user)


@router.get("/workflow-runs", response_model=list[WorkflowRunSummary])
def list_workflow_runs(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WorkflowRunSummary]:
    return service.list_runs(user)


@router.post("/workflow-runs", response_model=WorkflowRunSummary, status_code=status.HTTP_202_ACCEPTED)
def create_workflow_run(
    payload: WorkflowRunCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkflowRunSummary:
    return service.create_run(payload, user)


@router.post("/workflow-runs/{run_id}/approve", response_model=WorkflowRunSummary)
def approve_workflow_run(
    run_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkflowRunSummary:
    return service.approve_run(run_id, user)


@router.post("/workflow-runs/{run_id}/steps/{step_key}/complete", response_model=WorkflowRunSummary)
def complete_workflow_step(
    run_id: UUID,
    step_key: str,
    payload: WorkflowStepComplete,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkflowRunSummary:
    return service.complete_step(run_id, step_key, payload, user)
