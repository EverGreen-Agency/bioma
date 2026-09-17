import os
from pathlib import Path
import sys
from urllib.parse import urlparse

from cryptography.fernet import Fernet


os.environ.setdefault("SECRET_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))

SMOKE_DATABASE_URL = os.environ.get("BIOMA_SMOKE_DATABASE_URL")
if not SMOKE_DATABASE_URL:
    raise RuntimeError("Defina BIOMA_SMOKE_DATABASE_URL para executar smoke_vault.py fora do banco operacional.")
smoke_database_name = urlparse(SMOKE_DATABASE_URL).path.lstrip("/").lower()
if not smoke_database_name.endswith(("_test", "_smoke")):
    raise RuntimeError("BIOMA_SMOKE_DATABASE_URL deve apontar para um banco com sufixo _test ou _smoke.")
os.environ["DATABASE_URL"] = SMOKE_DATABASE_URL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
OPERATOR_EMAIL = "smoke-vault-operator@bioma.example.com"
VIEWER_EMAIL = "smoke-vault-viewer@bioma.example.com"
CLIENT_EMAIL = "smoke-vault-client@bioma.example.com"
PASSWORD = "senha-dev-123"
SECRET_VALUE = "vault-smoke-secret-value"


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


def credential_payload(label: str, visibility: str = "internal") -> dict:
    return {
        "platform": "Smoke Platform",
        "label": label,
        "account_hint": "conta de teste",
        "platform_url": "https://example.test/vault-smoke",
        "visibility": visibility,
        "secrets": {
            "username": "smoke-user",
            "email": "smoke@example.test",
            "password": SECRET_VALUE,
            "other_access": "Google Workspace",
        },
    }


def main() -> None:
    workspace_a = create_smoke_workspace("Vault A")
    workspace_b = create_smoke_workspace("Vault B")
    emails = [OPERATOR_EMAIL, VIEWER_EMAIL, CLIENT_EMAIL]
    operator_id = upsert_smoke_user(OPERATOR_EMAIL, "Vault Operator", PASSWORD)
    viewer_id = upsert_smoke_user(VIEWER_EMAIL, "Vault Viewer", PASSWORD)
    client_id = upsert_smoke_user(CLIENT_EMAIL, "Vault Client", PASSWORD)
    assign(workspace_a.workspace_id, operator_id, "operator")
    assign(workspace_a.workspace_id, viewer_id, "viewer")
    grant_client_user(workspace_a, client_id)

    admin = TestClient(app)
    operator = TestClient(app)
    viewer = TestClient(app)
    client_user = TestClient(app)

    try:
        for http_client, email in (
            (admin, ADMIN_EMAIL),
            (operator, OPERATOR_EMAIL),
            (viewer, VIEWER_EMAIL),
            (client_user, CLIENT_EMAIL),
        ):
            login(http_client, email)

        created = admin.post(
            f"/workspaces/{workspace_a.workspace_id}/vault",
            json=credential_payload("Interno"),
        )
        assert_status(created, 201, "admin creates internal credential")
        credential_id = created.json()["id"]
        assert "secrets" not in created.json()

        with connect() as conn:
            stored = conn.execute(
                "select encrypted_username, encrypted_email, encrypted_password, encrypted_other_access, platform_url from vault_credentials where id = %s",
                (credential_id,),
            ).fetchone()
        assert stored["encrypted_username"].startswith("enc:v1:")
        assert stored["encrypted_email"].startswith("enc:v1:")
        assert stored["encrypted_password"].startswith("enc:v1:")
        assert stored["encrypted_other_access"].startswith("enc:v1:")
        assert SECRET_VALUE not in stored["encrypted_password"]
        assert stored["platform_url"] == "https://example.test/vault-smoke"

        for http_client, label in ((admin, "admin"), (operator, "operator"), (viewer, "viewer")):
            listed = http_client.get(f"/workspaces/{workspace_a.workspace_id}/vault")
            assert_status(listed, 200, f"{label} lists metadata")
            assert SECRET_VALUE not in listed.text

        client_list = client_user.get(f"/workspaces/{workspace_a.workspace_id}/vault")
        assert_status(client_list, 200, "client lists visible metadata")
        assert all(row["id"] != credential_id for row in client_list.json())

        assert_status(
            viewer.post(f"/workspaces/{workspace_a.workspace_id}/vault", json=credential_payload("Forbidden")),
            403,
            "viewer cannot create",
        )
        operator_created = operator.post(
            f"/workspaces/{workspace_a.workspace_id}/vault",
            json=credential_payload("Operator"),
        )
        assert_status(operator_created, 201, "operator creates without reveal capability")
        assert_status(
            operator.post(
                f"/workspaces/{workspace_a.workspace_id}/vault/{credential_id}/reveal",
                json={"reason": "smoke operator"},
            ),
            403,
            "operator cannot reveal",
        )

        deposited = client_user.post(
            f"/workspaces/{workspace_a.workspace_id}/vault",
            json=credential_payload("Entregue pelo cliente", visibility="internal"),
        )
        assert_status(deposited, 201, "client deposits credential")
        assert deposited.json()["visibility"] == "client"
        assert_status(
            client_user.post(
                f"/workspaces/{workspace_a.workspace_id}/vault/{deposited.json()['id']}/reveal",
                json={"reason": "smoke client"},
            ),
            403,
            "client cannot reveal own deposit",
        )
        assert_status(
            client_user.get(f"/workspaces/{workspace_b.workspace_id}/vault"),
            404,
            "client A cannot list workspace B",
        )

        revealed = admin.post(
            f"/workspaces/{workspace_a.workspace_id}/vault/{credential_id}/reveal",
            json={"reason": "configuração do smoke"},
        )
        assert_status(revealed, 200, "admin reveals with reason")
        assert revealed.json()["secrets"]["password"] == SECRET_VALUE
        assert revealed.json()["secrets"]["email"] == "smoke@example.test"
        assert revealed.json()["secrets"]["other_access"] == "Google Workspace"

        copied = admin.post(
            f"/workspaces/{workspace_a.workspace_id}/vault/{credential_id}/copy",
            json={"reason": "cópia auditada do smoke", "field": "username"},
        )
        assert_status(copied, 200, "admin copies audited field")
        assert copied.json()["value"] == "smoke-user"

        rotated = operator.patch(
            f"/workspaces/{workspace_a.workspace_id}/vault/{credential_id}",
            json={"secrets": {"password": "rotated-smoke-secret"}},
        )
        assert_status(rotated, 200, "operator rotates secret")
        assert rotated.json()["version"] == 2

        compromised = operator.patch(
            f"/workspaces/{workspace_a.workspace_id}/vault/{credential_id}/status",
            json={"status": "compromised"},
        )
        assert_status(compromised, 200, "operator marks compromised")
        assert_status(
            admin.post(
                f"/workspaces/{workspace_a.workspace_id}/vault/{credential_id}/reveal",
                json={"reason": "should be blocked"},
            ),
            409,
            "compromised credential cannot reveal",
        )

        with connect() as conn:
            audit_events = {
                row["event_type"]
                for row in conn.execute(
                    "select event_type from audit_logs where organization_id = %s and event_type like 'vault.%%'",
                    (workspace_a.organization_id,),
                ).fetchall()
            }
        assert {
            "vault.credential_created",
            "vault.credential_revealed",
            "vault.credential_copied",
            "vault.credential_updated",
            "vault.credential_status_changed",
        }.issubset(audit_events)
    finally:
        cleanup_smoke_data([workspace_a.organization_id, workspace_b.organization_id], emails)

    print("vault smoke ok")


if __name__ == "__main__":
    main()
