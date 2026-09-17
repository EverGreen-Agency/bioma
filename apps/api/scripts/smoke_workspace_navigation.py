from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-navigation-client@bioma.example.com"
PASSWORD = "senha-dev-123"
VIEW_NAME = "Smoke Minha carteira"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert_status(response, 200, f"login {email}")


def cleanup(organization_ids=None) -> None:
    with connect() as conn:
        conn.execute("delete from workspace_saved_views where name = %s", (VIEW_NAME,))
    cleanup_smoke_data(organization_ids or [], [CLIENT_EMAIL])


def main() -> None:
    cleanup()
    smoke_workspace = create_smoke_workspace("Navigation")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Navigation Client", PASSWORD)
    grant_client_user(smoke_workspace, client_user_id)
    admin = TestClient(app)
    client_user = TestClient(app)
    login(admin, ADMIN_EMAIL)
    login(client_user, CLIENT_EMAIL)

    try:
        workspaces_response = admin.get("/workspaces")
        assert_status(workspaces_response, 200, "list workspaces")
        workspaces = workspaces_response.json()
        hm = next(row for row in workspaces if row["id"] == str(smoke_workspace.workspace_id))
        internal = next(row for row in workspaces if row["kind"] == "agency_internal")
        assert "is_favorite" in hm and "is_assigned" in hm

        favorites = admin.put(f"/workspaces/{hm['id']}/favorite")
        assert_status(favorites, 200, "favorite workspace")
        assert next(row for row in favorites.json() if row["id"] == hm["id"])["is_favorite"] is True

        assert_status(
            client_user.put(f"/workspaces/{internal['id']}/favorite"),
            404,
            "cannot favorite inaccessible workspace",
        )

        created = admin.post(
            "/workspaces/views",
            json={
                "tenant_organization_id": hm["tenant_organization_id"],
                "name": VIEW_NAME,
                "filters": {
                    "query": "HM",
                    "kinds": ["client"],
                    "access_roles": [],
                    "statuses": ["active"],
                    "favorite_only": True,
                    "mine_only": False,
                },
            },
        )
        assert_status(created, 201, "create saved view")
        view = created.json()
        assert view["filters"]["favorite_only"] is True
        assert_status(
            admin.post(
                "/workspaces/views",
                json={
                    "tenant_organization_id": hm["tenant_organization_id"],
                    "name": VIEW_NAME,
                    "filters": {"query": ""},
                },
            ),
            409,
            "duplicate saved view",
        )
        listed = admin.get("/workspaces/views")
        assert_status(listed, 200, "list saved views")
        assert any(row["id"] == view["id"] for row in listed.json())
        assert_status(admin.delete(f"/workspaces/views/{view['id']}"), 200, "delete saved view")

        unfavorite = admin.delete(f"/workspaces/{hm['id']}/favorite")
        assert_status(unfavorite, 200, "unfavorite workspace")
        assert next(row for row in unfavorite.json() if row["id"] == hm["id"])["is_favorite"] is False
    finally:
        cleanup([smoke_workspace.organization_id])

    print("workspace navigation smoke ok")


if __name__ == "__main__":
    main()
