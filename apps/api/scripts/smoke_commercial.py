from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
OPERATOR_EMAIL = "smoke-commercial-operator@bioma.example.com"
CLIENT_EMAIL = "smoke-commercial-client@bioma.example.com"
OTHER_CLIENT_EMAIL = "smoke-commercial-other@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert_status(response, 200, f"login {email}")


def assign(workspace_id, user_id, role: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            insert into workspace_assignments (workspace_id, user_id, role)
            values (%s, %s, %s)
            on conflict (workspace_id, user_id) where user_id is not null
            do update set role = excluded.role, updated_at = now()
            """,
            (workspace_id, user_id, role),
        )


def main() -> None:
    workspace_a = create_smoke_workspace("Commercial Raio-X A")
    workspace_b = create_smoke_workspace("Commercial Raio-X B")
    emails = [OPERATOR_EMAIL, CLIENT_EMAIL, OTHER_CLIENT_EMAIL]

    operator_id = upsert_smoke_user(OPERATOR_EMAIL, "Commercial Operator", PASSWORD)
    client_id = upsert_smoke_user(CLIENT_EMAIL, "Commercial Client A", PASSWORD)
    other_client_id = upsert_smoke_user(OTHER_CLIENT_EMAIL, "Commercial Client B", PASSWORD)

    assign(workspace_a.workspace_id, operator_id, "operator")
    grant_client_user(workspace_a, client_id)
    grant_client_user(workspace_b, other_client_id)

    admin_client = TestClient(app)
    operator_client = TestClient(app)
    user_client = TestClient(app)
    other_user_client = TestClient(app)

    try:
        login(admin_client, ADMIN_EMAIL)
        login(operator_client, OPERATOR_EMAIL)
        login(user_client, CLIENT_EMAIL)
        login(other_user_client, OTHER_CLIENT_EMAIL)

        # 1. Fetch initial commercial portal (default scores 0.0, regua_level 1)
        res = admin_client.get(f"/workspaces/{workspace_a.workspace_id}/commercial")
        assert_status(res, 200, "fetch commercial portal initial")
        data = res.json()
        assert data["scores"]["oferta_score"] == 0.0
        assert data["scores"]["demanda_score"] == 0.0
        assert data["scores"]["conversao_score"] == 0.0
        assert data["scores"]["oferta_level"] == 1
        assert data["scores"]["maturity_level"] == "semente"

        # 2. Operator submits diagnostic answer for Oferta Level 1 (score 5.0) -> Triggers graduation to Level 2
        res = operator_client.post(
            f"/workspaces/{workspace_a.workspace_id}/commercial/diagnostic",
            json={
                "pilar": "oferta",
                "regua_level": 1,
                "question_key": "proposta_padronizada",
                "score_value": 5.0,
                "notes": "Proposta v3 enviada a todos os leads",
            },
        )
        assert_status(res, 200, "operator submits diagnostic answer")
        data = res.json()
        assert data["scores"]["oferta_score"] == 5.0
        assert data["scores"]["oferta_level"] == 1  # Respeita nivel 1 sem graduar automaticamente
        assert len(data["answers"]) == 1
        assert data["answers"][0]["question_key"] == "proposta_padronizada"

        # 3. Client user cannot mutate diagnostic answers
        res = user_client.post(
            f"/workspaces/{workspace_a.workspace_id}/commercial/diagnostic",
            json={
                "pilar": "demanda",
                "regua_level": 1,
                "question_key": "midia_paga",
                "score_value": 8.0,
            },
        )
        assert_status(res, 403, "client user cannot mutate diagnostic")

        # 4. Client from workspace B cannot access workspace A commercial portal
        res = other_user_client.get(f"/workspaces/{workspace_a.workspace_id}/commercial")
        assert_status(res, 404, "other client cannot read workspace A commercial portal")

        # 5. Operator creates Action Plan for pilar gargalo
        gargalo = data["scores"]["gargalo_prioritario"]
        res = operator_client.post(
            f"/workspaces/{workspace_a.workspace_id}/commercial/action-plans",
            json={
                "pilar_gargalo": gargalo,
                "sprint_title": "Sprint 90 Dias - Estruturação de Demanda",
                "sprint_goals": "Implementar campanhas de tráfego pago e tracking de conversoes no GA4",
            },
        )
        assert_status(res, 200, "operator creates action plan")
        data = res.json()
        assert len(data["action_plans"]) == 1
        plan = data["action_plans"][0]
        assert plan["sprint_title"] == "Sprint 90 Dias - Estruturação de Demanda"
        assert plan["status"] == "em_andamento"

        # 6. Operator updates Action Plan status to 'concluido'
        plan_id = plan["id"]
        res = operator_client.patch(
            f"/workspaces/{workspace_a.workspace_id}/commercial/action-plans/{plan_id}",
            json={"status": "concluido"},
        )
        assert_status(res, 200, "operator updates action plan status")
        data = res.json()
        assert data["action_plans"][0]["status"] == "concluido"

    finally:
        cleanup_smoke_data([workspace_a.organization_id, workspace_b.organization_id], emails)

    print("commercial smoke ok")


if __name__ == "__main__":
    main()
