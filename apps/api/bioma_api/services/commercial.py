from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.db import connect
from bioma_api.repositories import commercial as commercial_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.commercial import (
    ActionPlanCreateRequest,
    ActionPlanStatusUpdateRequest,
    ActionPlanSummary,
    CommercialPortalResponse,
    CommercialScoreSummary,
    DiagnosticAnswerRequest,
    DiagnosticAnswerSummary,
)


def _require_workspace_access(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace não encontrado ou sem acesso.",
        )
    require_client_module(client, user, "commercial")
    if capability:
        require_workspace_capability(client, user, capability)
    return client


def get_commercial_portal(workspace_id: UUID, user: CurrentUserResponse) -> CommercialPortalResponse:
    with connect() as conn:
        _require_workspace_access(conn, workspace_id, user)
        scores_row = commercial_repo.get_commercial_scores(conn, workspace_id)
        answers_rows = commercial_repo.get_diagnostic_answers(conn, workspace_id)
        plans_rows = commercial_repo.list_action_plans(conn, workspace_id)

    scores = CommercialScoreSummary(**dict(scores_row))
    answers = [DiagnosticAnswerSummary(**dict(r)) for r in answers_rows]
    plans = [ActionPlanSummary(**dict(r)) for r in plans_rows]

    return CommercialPortalResponse(scores=scores, answers=answers, action_plans=plans)


def answer_diagnostic_question(
    workspace_id: UUID,
    payload: DiagnosticAnswerRequest,
    user: CurrentUserResponse,
) -> CommercialPortalResponse:
    with connect() as conn:
        _require_workspace_access(conn, workspace_id, user, capability="manage_work")

        commercial_repo.upsert_diagnostic_answer(
            conn,
            workspace_id,
            payload.pilar,
            payload.regua_level,
            payload.question_key.strip(),
            payload.score_value,
            payload.notes,
        )

    return get_commercial_portal(workspace_id, user)


def create_action_plan(
    workspace_id: UUID,
    payload: ActionPlanCreateRequest,
    user: CurrentUserResponse,
) -> CommercialPortalResponse:
    with connect() as conn:
        _require_workspace_access(conn, workspace_id, user, capability="manage_work")

        commercial_repo.create_action_plan(
            conn,
            workspace_id,
            payload.pilar_gargalo,
            payload.sprint_title.strip(),
            payload.sprint_goals.strip(),
        )

    return get_commercial_portal(workspace_id, user)


def update_action_plan_status(
    workspace_id: UUID,
    plan_id: UUID,
    payload: ActionPlanStatusUpdateRequest,
    user: CurrentUserResponse,
) -> CommercialPortalResponse:
    with connect() as conn:
        _require_workspace_access(conn, workspace_id, user, capability="manage_work")

        updated = commercial_repo.update_action_plan_status(conn, plan_id, payload.status)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plano de ação não encontrado.",
            )

    return get_commercial_portal(workspace_id, user)
