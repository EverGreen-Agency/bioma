"""Smoke do módulo de logística de kits (mod-logistica-kits): peças, kits e
envios por cliente. EG-admin only; client_user recebe 403. Self-clean.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from bioma_api.db import connect  # noqa: E402
from bioma_api.main import app  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user  # noqa: E402

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-kits-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    assert_status(client.post("/auth/login", json={"email": email, "password": PASSWORD}), 200, f"login {email}")


def main() -> None:
    workspace = create_smoke_workspace("Kits")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Kits Client", PASSWORD)
    grant_client_user(workspace, client_user_id)

    admin = TestClient(app)
    client_user = TestClient(app)
    piece_id = None
    kit_definition_id = None

    try:
        login(admin, ADMIN_EMAIL)
        login(client_user, CLIENT_EMAIL)

        # Cliente comum não acessa a logística interna.
        assert_status(client_user.get("/backoffice/logistics/pieces"), 403, "cliente bloqueado em pieces")

        piece = admin.post(
            "/backoffice/logistics/pieces",
            json={"name": "Camiseta smoke", "supplier": "Fornecedor Smoke", "unit_cost_cents": 5000, "stock_qty": 20},
        )
        assert_status(piece, 201, "criar peça")
        piece_id = piece.json()["id"]
        assert piece.json()["stock_qty"] == 20

        listed_pieces = admin.get("/backoffice/logistics/pieces")
        assert_status(listed_pieces, 200, "listar peças")
        assert any(row["id"] == piece_id for row in listed_pieces.json())

        updated_piece = admin.patch(f"/backoffice/logistics/pieces/{piece_id}", json={"stock_qty": 15})
        assert_status(updated_piece, 200, "atualizar estoque da peça")
        assert updated_piece.json()["stock_qty"] == 15

        # Kit referenciando peça inexistente: 422 controlado.
        bad_kit = admin.post(
            "/backoffice/logistics/kits",
            json={
                "name": "Kit inválido",
                "level": "starter",
                "pieces": [{"piece_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}],
            },
        )
        assert_status(bad_kit, 422, "kit com peça inexistente")

        kit = admin.post(
            "/backoffice/logistics/kits",
            json={
                "name": "Kit High-End Smoke",
                "level": "high-end",
                "description": "Kit de teste do smoke.",
                "pieces": [{"piece_id": piece_id, "quantity": 2}],
            },
        )
        assert_status(kit, 201, "criar kit")
        kit_definition_id = kit.json()["id"]
        assert kit.json()["total_cost_cents"] == 10000, kit.json()  # 2 * 5000

        shipment = admin.post(
            "/backoffice/logistics/shipments",
            json={"kit_definition_id": kit_definition_id, "client_id": str(workspace.client_id), "notes": "Primeiro envio"},
        )
        assert_status(shipment, 201, "criar envio")
        shipment_id = shipment.json()["id"]
        assert shipment.json()["status"] == "em_producao"
        assert shipment.json()["client_name"] == workspace.name

        sent = admin.patch(f"/backoffice/logistics/shipments/{shipment_id}/status", json={"status": "enviado"})
        assert_status(sent, 200, "marcar como enviado")
        assert sent.json()["shipped_at"] is not None

        delivered = admin.patch(f"/backoffice/logistics/shipments/{shipment_id}/status", json={"status": "entregue"})
        assert_status(delivered, 200, "marcar como entregue")
        assert delivered.json()["delivered_at"] is not None

        by_client = admin.get(f"/backoffice/logistics/shipments?client_id={workspace.client_id}")
        assert_status(by_client, 200, "listar envios por cliente")
        assert len(by_client.json()) == 1

        # Envio para cliente de outro tenant/inexistente: 404 controlado.
        bad_shipment = admin.post(
            "/backoffice/logistics/shipments",
            json={"kit_definition_id": kit_definition_id, "client_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert_status(bad_shipment, 404, "envio para cliente inexistente")

        print("kits/logistics smoke ok")
    finally:
        with connect() as conn:
            conn.execute("delete from kit_shipments where kit_definition_id = %s", (kit_definition_id,)) if kit_definition_id else None
            conn.execute("delete from kit_definitions where id = %s", (kit_definition_id,)) if kit_definition_id else None
            conn.execute("delete from kit_pieces where id = %s", (piece_id,)) if piece_id else None
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])


if __name__ == "__main__":
    main()
