from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import rh as rh_repo
from bioma_api.repositories import teams as teams_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.rh import (
    ManagerPortfolioResponse,
    ManagerPortfolioWorkspace,
    MilestoneCompletionRequest,
    MilestoneTemplateCreateRequest,
    MilestoneTemplateSummary,
    MilestoneTemplateUpdateRequest,
    OnboardingPlanCreateRequest,
    OnboardingPlanSummary,
    SatisfactionScoreCreateRequest,
    SatisfactionScoreSummary,
)


def _tenant_id(conn) -> UUID:
    # Não usa find_platform_tenant_id: exigiria eg_admin do chamador, mas
    # tenant_admin também deve operar aqui — o gate é _require_tenant_manager.
    tenant_id = workspaces_repo.find_eg_tenant_id(conn)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant administrativo não encontrado.")
    return tenant_id


def _require_tenant_manager(conn, tenant_organization_id: UUID, user: CurrentUserResponse) -> None:
    if is_platform_admin(user) or teams_repo.can_manage_tenant(conn, tenant_organization_id, user.id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente para gestão de RH.")


def list_milestone_templates(user: CurrentUserResponse) -> list[MilestoneTemplateSummary]:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        rows = rh_repo.list_milestone_templates(conn, tenant_id)
    return [MilestoneTemplateSummary(**row) for row in rows]


def create_milestone_template(payload: MilestoneTemplateCreateRequest, user: CurrentUserResponse) -> MilestoneTemplateSummary:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        row = rh_repo.create_milestone_template(conn, tenant_id, payload.model_dump())
        client_hub_repo.write_audit(conn, user.id, tenant_id, "onboarding_template.created", {"template_id": str(row["id"]), "day_offset": row["day_offset"]})
    return MilestoneTemplateSummary(**row)


def update_milestone_template(template_id: UUID, payload: MilestoneTemplateUpdateRequest, user: CurrentUserResponse) -> MilestoneTemplateSummary:
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        row = rh_repo.update_milestone_template(conn, tenant_id, template_id, updates)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marco não encontrado.")
        client_hub_repo.write_audit(conn, user.id, tenant_id, "onboarding_template.updated", {"template_id": str(template_id), "fields": sorted(updates)})
    return MilestoneTemplateSummary(**row)


def create_onboarding_plan(payload: OnboardingPlanCreateRequest, user: CurrentUserResponse) -> OnboardingPlanSummary:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        if rh_repo.find_existing_plan(conn, tenant_id, payload.user_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este funcionário já tem um plano de rampagem.")
        templates = rh_repo.active_milestone_templates(conn, tenant_id)
        milestones = [
            {"template_id": str(t["id"]), "day_offset": t["day_offset"], "title": t["title"], "status": "pending", "completed_at": None}
            for t in templates
        ]
        plan_id = rh_repo.create_onboarding_plan(conn, tenant_id, payload.user_id, payload.hire_date, milestones, user.id)
        client_hub_repo.write_audit(conn, user.id, tenant_id, "onboarding_plan.created", {"plan_id": str(plan_id), "user_id": str(payload.user_id)})
        row = rh_repo.get_onboarding_plan(conn, tenant_id, plan_id)
    return OnboardingPlanSummary(**row)


def list_onboarding_plans(user: CurrentUserResponse) -> list[OnboardingPlanSummary]:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        rows = rh_repo.list_onboarding_plans(conn, tenant_id)
    return [OnboardingPlanSummary(**row) for row in rows]


def update_milestone_status(plan_id: UUID, payload: MilestoneCompletionRequest, user: CurrentUserResponse) -> OnboardingPlanSummary:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        plan = rh_repo.get_onboarding_plan(conn, tenant_id, plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano de rampagem não encontrado.")
        if not any(m["day_offset"] == payload.day_offset for m in plan["milestones"]):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marco não encontrado neste plano.")
        rh_repo.update_milestone_status(conn, tenant_id, plan_id, payload.day_offset, payload.status)
        client_hub_repo.write_audit(conn, user.id, tenant_id, "onboarding_milestone.updated", {
            "plan_id": str(plan_id), "day_offset": payload.day_offset, "status": payload.status,
        })
        row = rh_repo.get_onboarding_plan(conn, tenant_id, plan_id)
    return OnboardingPlanSummary(**row)


def _managed_workspace(conn, workspace_id: UUID, user: CurrentUserResponse):
    workspace = teams_repo.find_workspace(conn, workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    _require_tenant_manager(conn, workspace["tenant_organization_id"], user)
    return workspace


def create_satisfaction_score(workspace_id: UUID, payload: SatisfactionScoreCreateRequest, user: CurrentUserResponse) -> SatisfactionScoreSummary:
    with connect() as conn:
        _managed_workspace(conn, workspace_id, user)
        row = rh_repo.create_satisfaction_score(conn, workspace_id, payload.model_dump(), user.id)
    return SatisfactionScoreSummary(**row)


def list_satisfaction_scores(workspace_id: UUID, user: CurrentUserResponse) -> list[SatisfactionScoreSummary]:
    with connect() as conn:
        _managed_workspace(conn, workspace_id, user)
        rows = rh_repo.list_satisfaction_scores(conn, workspace_id)
    return [SatisfactionScoreSummary(**row) for row in rows]


def manager_portfolio(manager_user_id: UUID, user: CurrentUserResponse) -> ManagerPortfolioResponse:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        if manager_user_id != user.id:
            _require_tenant_manager(conn, tenant_id, user)
        manager = conn.execute("select display_name from users where id = %s", (manager_user_id,)).fetchone()
        if not manager:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
        rows = rh_repo.list_managed_workspaces(conn, manager_user_id)
        satisfaction = rh_repo.latest_satisfaction_by_workspace(conn, [row["workspace_id"] for row in rows])

    workspaces = []
    for row in rows:
        total = row["deliverables_total"]
        done = row["deliverables_done"]
        overdue = row["deliverables_overdue"]
        blocked = row["deliverables_blocked"]
        completion = round((done / total) * 100, 1) if total else 0.0
        pace = "unknown" if not total else "off_track" if overdue else "at_risk" if blocked else "on_track"
        latest = satisfaction.get(row["workspace_id"])
        workspaces.append(ManagerPortfolioWorkspace(
            **row,
            completion_percentage=completion,
            pace_status=pace,
            latest_satisfaction_score=float(latest["score"]) if latest else None,
            latest_satisfaction_captured_at=latest["captured_at"] if latest else None,
        ))

    return ManagerPortfolioResponse(user_id=manager_user_id, user_name=manager["display_name"], workspaces=workspaces)
