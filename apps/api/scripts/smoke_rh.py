"""Smoke do módulo de RH (MOD-RH-001): marcos de rampagem configuráveis,
plano de onboarding por funcionário, satisfação/NPS por workspace e a
carteira/performance agregada de um gestor. Self-clean.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from bioma_api.db import connect  # noqa: E402
from bioma_api.main import app  # noqa: E402
from bioma_api.repositories import teams as teams_repo  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace, upsert_smoke_user  # noqa: E402

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
MANAGER_EMAIL = "smoke-rh-manager@bioma.example.com"
EMPLOYEE_EMAIL = "smoke-rh-employee@bioma.example.com"
OUTSIDER_EMAIL = "smoke-rh-outsider@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    assert_status(client.post("/auth/login", json={"email": email, "password": PASSWORD}), 200, f"login {email}")


def main() -> None:
    workspace = create_smoke_workspace("RH")
    manager_id = upsert_smoke_user(MANAGER_EMAIL, "RH Manager Smoke", PASSWORD)
    employee_id = upsert_smoke_user(EMPLOYEE_EMAIL, "RH Employee Smoke", PASSWORD)
    outsider_id = upsert_smoke_user(OUTSIDER_EMAIL, "RH Outsider Smoke", PASSWORD)

    with connect() as conn:
        teams_repo.upsert_tenant_membership(conn, workspace.tenant_id, manager_id, "tenant_admin")
        teams_repo.upsert_workspace_assignment(conn, workspace.workspace_id, manager_id, None, "workspace_manager", manager_id)

    admin = TestClient(app)
    manager = TestClient(app)
    outsider = TestClient(app)
    template_ids: list[str] = []
    plan_id = None

    try:
        login(admin, ADMIN_EMAIL)
        login(manager, MANAGER_EMAIL)
        login(outsider, OUTSIDER_EMAIL)

        # Outsider (sem tenant_admin) não gerencia RH.
        assert_status(outsider.get("/backoffice/rh/onboarding/templates"), 403, "outsider bloqueado em templates")

        for day in (15, 30, 60, 90):
            created = admin.post("/backoffice/rh/onboarding/templates", json={"day_offset": day, "title": f"Marco {day} dias smoke"})
            assert_status(created, 201, f"criar template dia {day}")
            template_ids.append(created.json()["id"])

        plan = admin.post("/backoffice/rh/onboarding/plans", json={"user_id": str(employee_id), "hire_date": "2026-07-01"})
        assert_status(plan, 201, "criar plano de rampagem")
        plan_id = plan.json()["id"]
        assert len(plan.json()["milestones"]) == 4, plan.json()

        # Plano duplicado para o mesmo funcionário: 409.
        duplicate = admin.post("/backoffice/rh/onboarding/plans", json={"user_id": str(employee_id), "hire_date": "2026-07-01"})
        assert_status(duplicate, 409, "plano duplicado")

        completed = admin.patch(f"/backoffice/rh/onboarding/plans/{plan_id}/milestone", json={"day_offset": 15, "status": "done"})
        assert_status(completed, 200, "concluir marco de 15 dias")
        milestone_15 = next(m for m in completed.json()["milestones"] if m["day_offset"] == 15)
        assert milestone_15["status"] == "done"
        assert milestone_15["completed_at"] is not None
        milestone_30 = next(m for m in completed.json()["milestones"] if m["day_offset"] == 30)
        assert milestone_30["status"] == "pending", "outros marcos não deveriam mudar"

        # Marco que não existe no plano: 404.
        bad_milestone = admin.patch(f"/backoffice/rh/onboarding/plans/{plan_id}/milestone", json={"day_offset": 999, "status": "done"})
        assert_status(bad_milestone, 404, "marco inexistente")

        # Satisfação/NPS do workspace.
        score = manager.post(f"/backoffice/rh/workspaces/{workspace.workspace_id}/satisfaction", json={"score": 9.5, "notes": "Cliente muito satisfeito"})
        assert_status(score, 201, "registrar satisfação")

        # Cria um projeto com uma entrega concluída para a carteira do gestor ter dado real.
        project = manager.post(
            f"/workspaces/{workspace.workspace_id}/projects",
            json={"name": "Projeto smoke RH", "project_type": "growth", "status": "active"},
        )
        assert_status(project, 201, "criar projeto para carteira")
        project_id = project.json()["id"]
        deliverable = manager.post(f"/projects/{project_id}/deliverables", json={"title": "Entrega smoke", "status": "done"})
        assert_status(deliverable, 201, "criar entrega concluída")

        portfolio = admin.get(f"/backoffice/rh/managers/{manager_id}/portfolio")
        assert_status(portfolio, 200, "carteira do gestor")
        body = portfolio.json()
        assert len(body["workspaces"]) == 1, body
        ws_row = body["workspaces"][0]
        assert ws_row["workspace_id"] == str(workspace.workspace_id)
        assert ws_row["deliverables_total"] == 1
        assert ws_row["deliverables_done"] == 1
        assert ws_row["completion_percentage"] == 100.0
        assert ws_row["pace_status"] == "on_track"
        assert ws_row["latest_satisfaction_score"] == 9.5

        # Gestor vê a própria carteira sem precisar ser tenant_admin de outro alguém.
        own_portfolio = manager.get(f"/backoffice/rh/managers/{manager_id}/portfolio")
        assert_status(own_portfolio, 200, "gestor ve a propria carteira")

        # Outsider não pode ver a carteira de outra pessoa.
        assert_status(outsider.get(f"/backoffice/rh/managers/{manager_id}/portfolio"), 403, "outsider bloqueado na carteira alheia")

        print("rh smoke ok")
    finally:
        with connect() as conn:
            if plan_id:
                conn.execute("delete from employee_onboarding_plans where id = %s", (plan_id,))
            for template_id in template_ids:
                conn.execute("delete from onboarding_milestone_templates where id = %s", (template_id,))
        cleanup_smoke_data([workspace.organization_id], [MANAGER_EMAIL, EMPLOYEE_EMAIL, OUTSIDER_EMAIL])


if __name__ == "__main__":
    main()
