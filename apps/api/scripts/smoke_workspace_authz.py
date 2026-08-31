from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-authz-client@bioma.example.com"
OPERATOR_EMAIL = "smoke-operator@bioma.example.com"
VIEWER_EMAIL = "smoke-viewer@bioma.example.com"
TENANT_ADMIN_EMAIL = "smoke-tenant-admin@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert_status(response, 200, f"login {email}")


def cleanup(organization_ids=None) -> None:
    with connect() as conn:
        conn.execute("delete from artifacts where title in ('Smoke RBAC', 'Should fail')")
        conn.execute("delete from teams where name = 'Smoke Carteira'")
    cleanup_smoke_data(
        organization_ids or [],
        [OPERATOR_EMAIL, VIEWER_EMAIL, TENANT_ADMIN_EMAIL, CLIENT_EMAIL],
    )


def main() -> None:
    cleanup()
    smoke_workspace = create_smoke_workspace("Authz")
    operator_id = upsert_smoke_user(OPERATOR_EMAIL, "Operador Smoke", PASSWORD)
    viewer_id = upsert_smoke_user(VIEWER_EMAIL, "Viewer Smoke", PASSWORD)
    tenant_admin_id = upsert_smoke_user(TENANT_ADMIN_EMAIL, "Tenant Admin Smoke", PASSWORD)
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Client Smoke", PASSWORD)
    grant_client_user(smoke_workspace, client_user_id)

    admin = TestClient(app)
    operator = TestClient(app)
    viewer = TestClient(app)
    tenant_admin = TestClient(app)
    client_user = TestClient(app)

    try:
        login(admin, ADMIN_EMAIL)
        login(client_user, CLIENT_EMAIL)
        workspaces = admin.get("/workspaces")
        assert_status(workspaces, 200, "admin workspaces")
        workspace_rows = workspaces.json()
        hm_workspace = next(row for row in workspace_rows if row["id"] == str(smoke_workspace.workspace_id))
        internal_workspace = next(row for row in workspace_rows if row["kind"] == "agency_internal")
        tenant_id = hm_workspace["tenant_organization_id"]

        team = admin.post(
            "/teams",
            json={"tenant_organization_id": tenant_id, "name": "Smoke Carteira"},
        )
        assert_status(team, 201, "create team")
        team_id = team.json()["id"]
        members = admin.put(
            f"/teams/{team_id}/members",
            json={"user_id": str(operator_id), "role": "manager"},
        )
        assert_status(members, 200, "assign team member")
        assert members.json()[0]["user_id"] == str(operator_id)

        assignments = admin.put(
            f"/workspaces/{hm_workspace['id']}/assignments",
            json={"team_id": team_id, "role": "operator"},
        )
        assert_status(assignments, 200, "assign team portfolio")

        assignments = admin.put(
            f"/workspaces/{hm_workspace['id']}/assignments",
            json={"user_id": str(viewer_id), "role": "viewer"},
        )
        assert_status(assignments, 200, "assign viewer")

        tenant_members = admin.put(
            f"/tenants/{tenant_id}/members",
            json={"user_id": str(tenant_admin_id), "role": "tenant_admin"},
        )
        assert_status(tenant_members, 200, "assign tenant admin")

        login(operator, OPERATOR_EMAIL)
        operator_workspaces = operator.get("/workspaces")
        assert_status(operator_workspaces, 200, "operator portfolio")
        assert [row["id"] for row in operator_workspaces.json()] == [hm_workspace["id"]]
        assert operator_workspaces.json()[0]["access_role"] == "operator"
        assert_status(operator.get(f"/workspaces/{hm_workspace['id']}"), 200, "operator assigned workspace")
        assert_status(operator.get(f"/workspaces/{internal_workspace['id']}"), 404, "operator internal isolation")

        created = operator.post(
            f"/workspaces/{hm_workspace['id']}/artifacts",
            json={"title": "Smoke RBAC", "kind": "note", "visibility": "client"},
        )
        assert_status(created, 201, "operator manages work")
        artifact = next(row for row in created.json()["artifacts"] if row["title"] == "Smoke RBAC")
        assert_status(
            operator.delete(f"/workspaces/{hm_workspace['id']}/artifacts/{artifact['id']}"),
            200,
            "operator cleanup artifact",
        )

        login(viewer, VIEWER_EMAIL)
        viewer_workspaces = viewer.get("/workspaces")
        assert_status(viewer_workspaces, 200, "viewer portfolio")
        assert viewer_workspaces.json()[0]["access_role"] == "viewer"
        assert_status(viewer.get(f"/workspaces/{hm_workspace['id']}"), 200, "viewer reads")
        assert_status(
            viewer.post(
                f"/workspaces/{hm_workspace['id']}/artifacts",
                json={"title": "Should fail", "kind": "note"},
            ),
            403,
            "viewer cannot mutate",
        )

        login(tenant_admin, TENANT_ADMIN_EMAIL)
        tenant_workspaces = tenant_admin.get("/workspaces")
        assert_status(tenant_workspaces, 200, "tenant admin workspaces")
        assert {row["id"] for row in tenant_workspaces.json()} >= {hm_workspace["id"], internal_workspace["id"]}
        assert all(row["access_role"] == "tenant_admin" for row in tenant_workspaces.json())
        assert_status(
            tenant_admin.get(f"/teams?tenant_organization_id={tenant_id}"),
            200,
            "tenant admin manages teams",
        )

        assert_status(
            client_user.get(f"/teams?tenant_organization_id={tenant_id}"),
            404,
            "client user cannot enumerate teams",
        )
        assert_status(
            client_user.get(f"/workspaces/{internal_workspace['id']}"),
            404,
            "client user cannot cross into internal operation",
        )
    finally:
        cleanup([smoke_workspace.organization_id])

    print("workspace authz smoke ok")


if __name__ == "__main__":
    main()
