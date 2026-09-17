"""Smoke do módulo de certificações (MOD-CERTIFICACOES-001): certificações de
funcionário e da própria EG, status calculado (active/expiring_soon/expired),
autoatendimento (usuário vê as próprias) vs. gate de tenant_admin. Self-clean.
"""

from datetime import date, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from bioma_api.db import connect  # noqa: E402
from bioma_api.main import app  # noqa: E402
from smoke_support import cleanup_smoke_data, upsert_smoke_user  # noqa: E402

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
EMPLOYEE_EMAIL = "smoke-cert-employee@bioma.example.com"
OUTSIDER_EMAIL = "smoke-cert-outsider@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    assert_status(client.post("/auth/login", json={"email": email, "password": PASSWORD}), 200, f"login {email}")


def main() -> None:
    employee_id = upsert_smoke_user(EMPLOYEE_EMAIL, "Cert Employee Smoke", PASSWORD)
    outsider_id = upsert_smoke_user(OUTSIDER_EMAIL, "Cert Outsider Smoke", PASSWORD)

    admin = TestClient(app)
    employee = TestClient(app)
    outsider = TestClient(app)
    created_ids: list[str] = []

    try:
        login(admin, ADMIN_EMAIL)
        login(employee, EMPLOYEE_EMAIL)
        login(outsider, OUTSIDER_EMAIL)

        # Outsider não gerencia certificações de terceiros.
        assert_status(outsider.post("/backoffice/certifications", json={
            "provider": "Google", "name": "Google Ads Search", "issued_at": "2026-01-01",
        }), 403, "outsider bloqueado ao criar")

        active = admin.post("/backoffice/certifications", json={
            "user_id": str(employee_id), "provider": "Google", "name": "Google Ads Search Certification",
            "issued_at": "2026-01-01", "expires_at": str(date.today() + timedelta(days=200)),
        })
        assert_status(active, 201, "criar certificação ativa")
        created_ids.append(active.json()["id"])
        assert active.json()["status"] == "active"
        assert active.json()["holder_name"] == "Cert Employee Smoke"

        expiring = admin.post("/backoffice/certifications", json={
            "user_id": str(employee_id), "provider": "Meta", "name": "Meta Blueprint",
            "issued_at": "2025-01-01", "expires_at": str(date.today() + timedelta(days=10)),
        })
        assert_status(expiring, 201, "criar certificação prestes a vencer")
        created_ids.append(expiring.json()["id"])
        assert expiring.json()["status"] == "expiring_soon"

        expired = admin.post("/backoffice/certifications", json={
            "user_id": str(employee_id), "provider": "HubSpot", "name": "HubSpot Inbound",
            "issued_at": "2020-01-01", "expires_at": "2021-01-01",
        })
        assert_status(expired, 201, "criar certificação vencida")
        created_ids.append(expired.json()["id"])
        assert expired.json()["status"] == "expired"

        agency = admin.post("/backoffice/certifications", json={
            "provider": "Google", "name": "Google Partner", "issued_at": "2026-01-01",
        })
        assert_status(agency, 201, "certificação da própria EG (sem user_id)")
        created_ids.append(agency.json()["id"])
        assert agency.json()["user_id"] is None
        assert agency.json()["holder_name"] == "EverGreen (agência)"
        assert agency.json()["status"] == "active", "sem expires_at nunca vence"

        # Autoatendimento: o próprio funcionário vê as suas certificações sem ser tenant_admin.
        own = employee.get(f"/backoffice/certifications?user_id={employee_id}")
        assert_status(own, 200, "funcionario ve as proprias certificacoes")
        assert len(own.json()) == 3

        # Mas não pode ver as certificações de outra pessoa.
        assert_status(outsider.get(f"/backoffice/certifications?user_id={employee_id}"), 403, "outsider bloqueado ao ver certificacoes alheias")

        updated = admin.patch(f"/backoffice/certifications/{active.json()['id']}", json={"credential_id": "cert-smoke-123"})
        assert_status(updated, 200, "atualizar certificação")
        assert updated.json()["credential_id"] == "cert-smoke-123"

        listing = admin.get("/backoffice/certifications")
        assert_status(listing, 200, "listar todas")
        assert len(listing.json()) >= 4

        deleted = admin.delete(f"/backoffice/certifications/{agency.json()['id']}")
        assert_status(deleted, 204, "excluir certificação")
        created_ids.remove(agency.json()["id"])
        assert_status(admin.delete(f"/backoffice/certifications/{agency.json()['id']}"), 404, "excluir de novo: 404")

        print("certifications smoke ok")
    finally:
        with connect() as conn:
            for cert_id in created_ids:
                conn.execute("delete from certifications where id = %s", (cert_id,))
        cleanup_smoke_data([], [EMPLOYEE_EMAIL, OUTSIDER_EMAIL])


if __name__ == "__main__":
    main()
