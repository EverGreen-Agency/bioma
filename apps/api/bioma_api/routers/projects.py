from uuid import UUID

from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.projects import (
    ContractCreate, ContractUpdate, ProjectCreate, ProjectDeliverableCreate, ProjectDetail,
    ProjectDocumentCreate, ProjectPhaseCreate, ProjectPhaseUpdate, ProjectSummary, ProjectUpdate,
    ProjectPlanApproveRequest, ProjectPlanGenerateRequest, ProjectPlanMaterializeRequest,
    PlanningPortfolioItem, ProjectPlanItemUpdate, ProjectPlanSummary, ProjectPlanningIntakeSummary, ProjectPlanningIntakeUpdate,
    ProjectPlanningIntakeWrite, ProjectUpdateCreate, ScopeItemCreate, ScopeItemUpdate,
)
from bioma_api.services import projects as project_service


workspace_router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["projects"])
router = APIRouter(tags=["projects"])


@router.get("/backoffice/planning-portfolio", response_model=list[PlanningPortfolioItem])
def list_planning_portfolio(user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.list_planning_portfolio(user)


@workspace_router.get("", response_model=list[ProjectSummary])
def list_projects(workspace_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.list_projects(workspace_id, user)


@workspace_router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(workspace_id: UUID, payload: ProjectCreate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.create_project(workspace_id, payload, user)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.get_project(project_id, user)


@router.patch("/projects/{project_id}", response_model=ProjectDetail)
def update_project(project_id: UUID, payload: ProjectUpdate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.update_project(project_id, payload, user)


@router.post("/projects/{project_id}/contracts", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_contract(project_id: UUID, payload: ContractCreate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.create_contract(project_id, payload, user)


@router.patch("/contracts/{contract_id}", response_model=ProjectDetail)
def update_contract(contract_id: UUID, payload: ContractUpdate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.update_contract(contract_id, payload, user)


@router.post("/contracts/{contract_id}/scope-items", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_scope_item(contract_id: UUID, payload: ScopeItemCreate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.create_scope_item(contract_id, payload, user)


@router.patch("/scope-items/{scope_item_id}", response_model=ProjectDetail)
def update_scope_item(scope_item_id: UUID, payload: ScopeItemUpdate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.update_scope_item(scope_item_id, payload, user)


@router.post("/projects/{project_id}/deliverables", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_deliverable(project_id: UUID, payload: ProjectDeliverableCreate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.create_deliverable(project_id, payload, user)


@router.post("/projects/{project_id}/phases", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_phase(project_id: UUID, payload: ProjectPhaseCreate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.create_phase(project_id, payload, user)


@router.patch("/project-phases/{phase_id}", response_model=ProjectDetail)
def update_phase(phase_id: UUID, payload: ProjectPhaseUpdate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.update_phase(phase_id, payload, user)


@router.post("/projects/{project_id}/documents", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_document(project_id: UUID, payload: ProjectDocumentCreate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.create_document(project_id, payload, user)


@router.post("/projects/{project_id}/updates", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project_update(project_id: UUID, payload: ProjectUpdateCreate, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.create_project_update(project_id, payload, user)


@router.get("/project-plans/{plan_id}", response_model=ProjectPlanSummary)
def get_project_plan(plan_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.get_project_plan(plan_id, user)


@router.post("/projects/{project_id}/plans/generate", response_model=ProjectPlanSummary, status_code=status.HTTP_201_CREATED)
def generate_project_plan(
    project_id: UUID,
    payload: ProjectPlanGenerateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return project_service.generate_project_plan(project_id, payload, user)


@router.get("/projects/{project_id}/planning-intake-schema/{schema_key}")
def get_planning_intake_schema(
    project_id: UUID,
    schema_key: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return project_service.get_planning_intake_schema(project_id, schema_key, user)


@router.get("/projects/{project_id}/planning-intakes", response_model=list[ProjectPlanningIntakeSummary])
def list_planning_intakes(project_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.list_project_planning_intakes(project_id, user)


@router.post("/projects/{project_id}/planning-intakes", response_model=ProjectPlanningIntakeSummary, status_code=status.HTTP_201_CREATED)
def create_planning_intake(
    project_id: UUID,
    payload: ProjectPlanningIntakeWrite,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return project_service.create_project_planning_intake(project_id, payload, user)


@router.patch("/project-planning-intakes/{intake_id}", response_model=ProjectPlanningIntakeSummary)
def update_planning_intake(
    intake_id: UUID,
    payload: ProjectPlanningIntakeUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return project_service.update_project_planning_intake(intake_id, payload, user)


@router.post("/project-planning-intakes/{intake_id}/finalize", response_model=ProjectPlanningIntakeSummary)
def finalize_planning_intake(intake_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return project_service.finalize_project_planning_intake(intake_id, user)


@router.post("/project-plans/{plan_id}/approve", response_model=ProjectPlanSummary)
def approve_project_plan(
    plan_id: UUID,
    payload: ProjectPlanApproveRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return project_service.approve_project_plan(plan_id, payload, user)


@router.patch("/project-plan-items/{item_id}", response_model=ProjectPlanSummary)
def update_project_plan_item(
    item_id: UUID,
    payload: ProjectPlanItemUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return project_service.update_project_plan_item(item_id, payload, user)


@router.post("/project-plans/{plan_id}/materialize", response_model=ProjectDetail)
def materialize_project_plan(
    plan_id: UUID,
    payload: ProjectPlanMaterializeRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return project_service.materialize_project_plan(plan_id, payload, user)
