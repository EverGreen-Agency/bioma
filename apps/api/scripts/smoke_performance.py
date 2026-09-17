from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "henrique@hmconexoes.com.br"
DEV_PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEV_PASSWORD})
    assert_status(response, 200, f"login {email}")


def main() -> None:
    admin = TestClient(app)
    client_user = TestClient(app)
    login(admin, ADMIN_EMAIL)
    login(client_user, CLIENT_EMAIL)

    clients = admin.get("/clients")
    assert_status(clients, 200, "listar clientes")
    hm_client_id = next(
        row["id"] for row in clients.json() if row["organization_slug"] == "hm-conexoes"
    )
    workspaces = admin.get("/workspaces")
    assert_status(workspaces, 200, "listar workspaces")
    hm_workspace_id = next(
        row["id"] for row in workspaces.json() if row["organization_slug"] == "hm-conexoes"
    )

    period = {"date_from": "2026-07-01", "date_to": "2026-07-31"}
    overview = admin.get(f"/workspaces/{hm_workspace_id}/performance", params=period)
    assert_status(overview, 200, "overview admin")
    overview_body = overview.json()
    assert overview_body["workspace_id"] == hm_workspace_id
    assert overview_body["client_id"] == hm_client_id
    assert overview_body["ads"]["impressions"] > 0
    assert overview_body["daily"]
    assert overview_body["freshness"]

    # Feature-gating (decisão 2026-07-14): analytics vem desabilitado por
    # default para client_user; o EG admin habilita por cliente.
    gated_overview = client_user.get(f"/workspaces/{hm_workspace_id}/performance", params=period)
    assert_status(gated_overview, 403, "overview cliente bloqueado por default")

    enable_analytics = admin.patch(
        f"/workspaces/{hm_workspace_id}",
        json={"enabled_modules": ["hub", "content", "files", "analytics"]},
    )
    assert_status(enable_analytics, 200, "habilitar módulo analytics")

    client_overview = client_user.get(f"/workspaces/{hm_workspace_id}/performance", params=period)
    assert_status(client_overview, 200, "overview cliente com módulo habilitado")

    revert_modules = admin.patch(
        f"/workspaces/{hm_workspace_id}",
        json={"enabled_modules": ["hub", "content", "files"]},
    )
    assert_status(revert_modules, 200, "reverter módulos ao default")

    endpoints = (
        ("google-ads/campaigns", "campanhas", period),
        ("ga4/acquisition", "aquisição GA4", period),
        ("search-console/queries", "consultas GSC", period),
        ("gtm/snapshots", "snapshots GTM", None),
    )
    for path, label, params in endpoints:
        response = admin.get(f"/workspaces/{hm_workspace_id}/performance/{path}", params=params)
        assert_status(response, 200, label)
        assert response.json(), f"seed deve popular {label}"
        if path == "gtm/snapshots":
            assert response.json()[0]["workspace_id"] == hm_workspace_id
            assert "gtm_workspace_id" in response.json()[0]

    blocked_sync = client_user.post(
        f"/workspaces/{hm_workspace_id}/performance/sync",
        json={"provider": "all", **period},
    )
    assert_status(blocked_sync, 403, "cliente não pode sincronizar")

    queued_sync = admin.post(
        f"/workspaces/{hm_workspace_id}/performance/sync",
        json={"provider": "all", **period},
    )
    assert_status(queued_sync, 202, "admin enfileira sync")
    assert queued_sync.json()["status"] == "queued"
    assert queued_sync.json()["workspace_id"] == hm_workspace_id
    queued_sync_id = queued_sync.json()["id"]

    portal_with_queued_sync = admin.get(f"/workspaces/{hm_workspace_id}")
    assert_status(portal_with_queued_sync, 200, "portal aceita sync enfileirado")
    assert any(item["id"] == queued_sync_id for item in portal_with_queued_sync.json()["sync_runs"])

    suffix = uuid4().hex[:8]
    created = admin.post(
        "/clients",
        json={
            "name": f"Performance Smoke {suffix}",
            "organization_name": f"Performance Smoke {suffix}",
            "status": "onboarding",
        },
    )
    assert_status(created, 201, "criar cliente isolado")
    created_client_id = created.json()["client"]["id"]
    created_org_id = created.json()["client"]["organization_id"]
    created_workspace_id = next(
        row["id"] for row in admin.get("/workspaces").json() if row["organization_id"] == created_org_id
    )

    hidden = client_user.get(f"/workspaces/{created_workspace_id}/performance")
    assert_status(hidden, 404, "BOLA performance")

    connection = admin.post(
        f"/workspaces/{created_workspace_id}/performance/connections",
        json={
            "provider": "ga4",
            "external_account_id": "properties/123456",
            "display_name": "GA4 smoke",
            "credentials_ref": "env:GOOGLE_SERVICE_ACCOUNT_JSON",
        },
    )
    assert_status(connection, 201, "criar conexão")
    assert connection.json()[0]["workspace_id"] == created_workspace_id

    mismatch_rejected = False
    try:
        with connect() as conn:
            conn.execute(
                """
                insert into performance_connections (
                  client_id, organization_id, workspace_id, provider, external_account_id
                )
                values (%s, %s, %s, 'gtm', %s)
                """,
                (created_client_id, created_org_id, hm_workspace_id, f"mismatch-{suffix}"),
            )
    except Exception:
        mismatch_rejected = True
    assert mismatch_rejected, "dual-write deve rejeitar workspace de outro cliente"

    with connect() as conn:
        conn.execute("delete from sync_runs where id = %s", (queued_sync_id,))
        conn.execute("delete from organizations where id = %s", (created_org_id,))

    print("performance smoke ok")


if __name__ == "__main__":
    main()
