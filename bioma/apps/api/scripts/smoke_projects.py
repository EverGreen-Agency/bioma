from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
OPERATOR_EMAIL = "smoke-projects-operator@bioma.example.com"
VIEWER_EMAIL = "smoke-projects-viewer@bioma.example.com"
CLIENT_A_EMAIL = "smoke-projects-client-a@bioma.example.com"
CLIENT_B_EMAIL = "smoke-projects-client-b@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert_status(response, 200, f"login {email}")


def cleanup(organization_ids=None) -> None:
    cleanup_smoke_data(
        organization_ids or [],
        [OPERATOR_EMAIL, VIEWER_EMAIL, CLIENT_A_EMAIL, CLIENT_B_EMAIL],
    )


def assign(admin: TestClient, workspace_id, user_id, role: str) -> None:
    response = admin.put(
        f"/workspaces/{workspace_id}/assignments",
        json={"user_id": str(user_id), "role": role},
    )
    assert_status(response, 200, f"assign {role}")


def main() -> None:
    cleanup()
    workspace_a = create_smoke_workspace("Projects A")
    workspace_b = create_smoke_workspace("Projects B")
    operator_id = upsert_smoke_user(OPERATOR_EMAIL, "Projects Operator", PASSWORD)
    viewer_id = upsert_smoke_user(VIEWER_EMAIL, "Projects Viewer", PASSWORD)
    client_a_id = upsert_smoke_user(CLIENT_A_EMAIL, "Projects Client A", PASSWORD)
    client_b_id = upsert_smoke_user(CLIENT_B_EMAIL, "Projects Client B", PASSWORD)
    grant_client_user(workspace_a, client_a_id)
    grant_client_user(workspace_b, client_b_id)

    admin = TestClient(app)
    operator = TestClient(app)
    viewer = TestClient(app)
    client_a = TestClient(app)

    try:
        login(admin, ADMIN_EMAIL)
        assign(admin, workspace_a.workspace_id, operator_id, "operator")
        assign(admin, workspace_a.workspace_id, viewer_id, "viewer")
        login(operator, OPERATOR_EMAIL)
        login(viewer, VIEWER_EMAIL)
        login(client_a, CLIENT_A_EMAIL)

        created = operator.post(
            f"/workspaces/{workspace_a.workspace_id}/projects",
            json={
                "name": "Social recorrente",
                "code": "SMOKE-SOCIAL",
                "project_type": "social",
                "status": "active",
                "owner_user_id": str(operator_id),
                "objective": "Validar contrato, ritmo e aceite sem depender do ClickUp.",
            },
        )
        assert_status(created, 201, "operator creates project")
        project = created.json()
        project_id = project["id"]

        tech_created = operator.post(
            f"/workspaces/{workspace_a.workspace_id}/projects",
            json={
                "name": "Evolucao tecnica smoke",
                "code": "SMOKE-TECH",
                "project_type": "tech",
                "status": "active",
                "objective": "Dar visibilidade honesta de fases, testes e bloqueios.",
            },
        )
        assert_status(tech_created, 201, "operator creates tech project")
        tech_project_id = tech_created.json()["id"]

        phase_created = operator.post(
            f"/projects/{tech_project_id}/phases",
            json={
                "sequence": 1,
                "name": "Evolucao do aplicativo",
                "status": "development",
                "client_summary": "Implementacao em andamento; atualizacoes publicadas com contexto de testes e bloqueios.",
            },
        )
        assert_status(phase_created, 201, "create client-visible phase")
        phase_id = phase_created.json()["phases"][0]["id"]
        assert_status(
            operator.post(
                f"/projects/{tech_project_id}/documents",
                json={
                    "kind": "technical_spec",
                    "title": "Especificacao tecnica smoke",
                    "url": "https://example.test/especificacao-smoke",
                },
            ),
            201,
            "link technical document",
        )
        assert_status(
            operator.post(
                f"/projects/{tech_project_id}/documents",
                json={
                    "kind": "proposal",
                    "title": "Proposta interna smoke",
                    "url": "https://example.test/proposta-interna-smoke",
                    "client_visible": False,
                },
            ),
            201,
            "link internal proposal",
        )
        assert_status(
            operator.post(
                f"/projects/{tech_project_id}/updates",
                json={
                    "phase_id": phase_id,
                    "kind": "blocker",
                    "summary": "Dia dedicado a corrigir uma inconsistencia de integracao.",
                    "detail": "Nao houve nova entrega liberada hoje; o proximo passo e retomar os testes de integracao.",
                },
            ),
            201,
            "publish honest client update",
        )
        assert_status(
            operator.post(
                f"/projects/{tech_project_id}/updates",
                json={
                    "phase_id": phase_id,
                    "kind": "note",
                    "summary": "Anotacao interna smoke",
                    "client_visible": False,
                },
            ),
            201,
            "create internal project update",
        )
        phase_deliverable = operator.post(
            f"/projects/{tech_project_id}/deliverables",
            json={"title": "Teste de integracao", "phase_id": phase_id, "status": "in_progress"},
        )
        assert_status(phase_deliverable, 201, "create phase deliverable")
        assert_status(
            operator.patch(f"/project-phases/{phase_id}", json={"status": "internal_testing"}),
            200,
            "update phase status",
        )

        assert_status(viewer.get(f"/projects/{project_id}"), 200, "viewer reads project")
        assert_status(
            viewer.patch(f"/projects/{project_id}", json={"status": "on_hold"}),
            403,
            "viewer cannot mutate project",
        )
        assert_status(client_a.get(f"/projects/{project_id}"), 200, "client reads visible project")
        tech_client_view = client_a.get(f"/projects/{tech_project_id}")
        assert_status(tech_client_view, 200, "client reads visible tech project")
        assert len(tech_client_view.json()["phases"]) == 1
        assert len(tech_client_view.json()["documents"]) == 1
        assert len(tech_client_view.json()["updates"]) == 1
        assert tech_client_view.json()["phases"][0]["status"] == "internal_testing"
        assert_status(
            client_a.post(
                f"/projects/{project_id}/contracts",
                json={"title": "Should fail"},
            ),
            403,
            "client cannot mutate project",
        )

        invalid_owner = operator.patch(
            f"/projects/{project_id}",
            json={"owner_user_id": str(client_b_id)},
        )
        assert_status(invalid_owner, 422, "owner must belong to workspace")

        contracted = operator.post(
            f"/projects/{project_id}/contracts",
            json={
                "title": "Contrato Social 2026",
                "version": 1,
                "status": "active",
                "starts_at": "2026-07-01",
                "ends_at": "2027-06-30",
                "total_value": "24000.00",
            },
        )
        assert_status(contracted, 201, "create contract")
        contract_id = contracted.json()["contracts"][0]["id"]

        scoped = operator.post(
            f"/contracts/{contract_id}/scope-items",
            json={
                "title": "Posts Instagram",
                "quantity": "12",
                "unit": "post",
                "cadence": "monthly",
                "acceptance_required": True,
                "acceptance_criteria": "Conteúdo aprovado pelo cliente.",
            },
        )
        assert_status(scoped, 201, "create contract scope")
        scope_id = scoped.json()["contracts"][0]["scope_items"][0]["id"]

        overdue = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        delivered = operator.post(
            f"/projects/{project_id}/deliverables",
            json={
                "title": "Post smoke",
                "scope_item_id": scope_id,
                "status": "blocked",
                "due_at": overdue,
            },
        )
        assert_status(delivered, 201, "create scoped deliverable")
        deliverable_id = delivered.json()["deliverables"][0]["id"]
        assert delivered.json()["pace_status"] == "off_track"

        completed = operator.patch(
            f"/workspaces/{workspace_a.workspace_id}/deliverables/{deliverable_id}",
            json={"status": "done"},
        )
        assert_status(completed, 200, "complete deliverable")
        refreshed = operator.get(f"/projects/{project_id}")
        assert_status(refreshed, 200, "read completed project")
        assert refreshed.json()["deliverables_done"] == 1
        assert refreshed.json()["deliverables"][0]["completed_at"] is not None
        assert refreshed.json()["completion_percentage"] == 100.0

        hidden = admin.post(
            f"/workspaces/{workspace_a.workspace_id}/projects",
            json={"name": "Projeto interno", "client_visible": False},
        )
        assert_status(hidden, 201, "admin creates internal project")
        hidden_id = hidden.json()["id"]
        assert_status(viewer.get(f"/projects/{hidden_id}"), 200, "viewer reads internal project")
        assert_status(client_a.get(f"/projects/{hidden_id}"), 404, "client cannot read internal project")
        client_list = client_a.get(f"/workspaces/{workspace_a.workspace_id}/projects")
        assert_status(client_list, 200, "client lists projects")
        # Igualdade e nao superset, de proposito: a assercao existe para
        # provar que o projeto INTERNO nao vaza, e `>=` deixaria de provar
        # isso. O terceiro id e o projeto padrao que create_smoke_workspace
        # passou a criar (decisao 13: tarefa de cliente exige projeto).
        assert {row["id"] for row in client_list.json()} == {
            project_id, tech_project_id, str(workspace_a.project_id)
        }

        hidden_contract = admin.post(
            f"/projects/{hidden_id}/contracts",
            json={"title": "Contrato interno"},
        )
        assert_status(hidden_contract, 201, "create internal contract")
        hidden_contract_id = hidden_contract.json()["contracts"][0]["id"]
        hidden_scope = admin.post(
            f"/contracts/{hidden_contract_id}/scope-items",
            json={"title": "Escopo interno"},
        )
        assert_status(hidden_scope, 201, "create internal scope")
        foreign_scope_id = hidden_scope.json()["contracts"][0]["scope_items"][0]["id"]
        assert_status(
            operator.post(
                f"/projects/{project_id}/deliverables",
                json={"title": "Wrong project", "scope_item_id": foreign_scope_id},
            ),
            422,
            "scope must belong to project",
        )
        hidden_phase = admin.post(
            f"/projects/{hidden_id}/phases",
            json={"sequence": 1, "name": "Fase de outro projeto"},
        )
        assert_status(hidden_phase, 201, "create foreign project phase")
        assert_status(
            operator.post(
                f"/projects/{tech_project_id}/deliverables",
                json={"title": "Wrong phase", "phase_id": hidden_phase.json()["phases"][0]["id"]},
            ),
            422,
            "phase must belong to project",
        )

        project_b = admin.post(
            f"/workspaces/{workspace_b.workspace_id}/projects",
            json={"name": "Client B project"},
        )
        assert_status(project_b, 201, "create client B project")
        assert_status(
            client_a.get(f"/projects/{project_b.json()['id']}"),
            404,
            "client A cannot read client B",
        )
        assert_status(
            client_a.patch(f"/projects/{project_b.json()['id']}", json={"status": "archived"}),
            404,
            "client A cannot mutate client B",
        )

        with connect() as conn:
            events = conn.execute(
                "select event_type from audit_logs where metadata ->> 'project_id' = %s",
                (project_id,),
            ).fetchall()
        assert {row["event_type"] for row in events} >= {
            "project.created",
            "project.contract_created",
            "project.scope_item_created",
            "project.deliverable_created",
        }
    finally:
        cleanup([workspace_a.organization_id, workspace_b.organization_id])

    print("projects smoke ok")


if __name__ == "__main__":
    main()
