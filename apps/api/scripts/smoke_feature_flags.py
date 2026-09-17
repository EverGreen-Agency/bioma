"""Smoke dos feature flags por organização, contra o Postgres real.

Valida:
- sem linha no banco, vale o default do catálogo em código (nenhuma feature
  depende de seed);
- `coming_soon` aparece na listagem mas NÃO é acessível (é vitrine);
- escrita é EG-only; leitura é permitida a quem enxerga a organização;
- feature fora do catálogo é recusada (422), não gravada silenciosamente;
- remover a exceção devolve ao default.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.feature_flags import FEATURE_CATALOG, default_state
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-flags-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    workspace = create_smoke_workspace("FLAGS")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Flags Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)
    # Limpeza garantida mesmo se a falha acontecer antes do try/finally:
    # sem isto, uma assercao quebrada deixa o workspace na carteira.
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    organization_id = str(workspace.organization_id)

    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    try:
        # 1) Sem override, vale o default do catálogo.
        listing = admin.get(f"/organizations/{organization_id}/feature-flags")
        assert_status(listing, 200, "listar flags")
        flags = {row["feature_key"]: row for row in listing.json()}
        assert set(flags) == set(FEATURE_CATALOG), f"catalogo divergente: {set(flags) ^ set(FEATURE_CATALOG)}"
        for key, row in flags.items():
            assert row["state"] == default_state(key), f"{key}: {row['state']} != default {default_state(key)}"
            assert row["is_override"] is False, f"{key} nao deveria ser override"
        print(f"defaults do catalogo OK ({len(flags)} features, nenhuma dependendo de seed)")

        # 2) coming_soon aparece mas nao e acessivel.
        updated = admin.put(
            f"/organizations/{organization_id}/feature-flags",
            json={"feature_key": "local_radar", "state": "coming_soon", "note": "smoke"},
        )
        assert_status(updated, 200, "definir coming_soon")
        radar = next(row for row in updated.json() if row["feature_key"] == "local_radar")
        assert radar["state"] == "coming_soon" and radar["is_override"] is True, radar
        assert radar["accessible"] is False, "coming_soon nao pode ser acessivel"
        print("coming_soon: visivel mas nao acessivel OK")

        # 3) beta e acessivel.
        updated = admin.put(
            f"/organizations/{organization_id}/feature-flags",
            json={"feature_key": "local_radar", "state": "beta"},
        )
        assert_status(updated, 200, "definir beta")
        radar = next(row for row in updated.json() if row["feature_key"] == "local_radar")
        assert radar["accessible"] is True, radar
        print("beta: acessivel OK")

        # 4) Cliente le, mas nao escreve.
        client_listing = client_user.get(f"/organizations/{organization_id}/feature-flags")
        assert_status(client_listing, 200, "cliente le flags")
        assert_status(
            client_user.put(
                f"/organizations/{organization_id}/feature-flags",
                json={"feature_key": "local_radar", "state": "active"},
            ),
            403,
            "cliente nao escreve flag",
        )
        print("leitura pelo cliente OK, escrita 403 OK")

        # 5) Feature fora do catalogo e recusada.
        assert_status(
            admin.put(
                f"/organizations/{organization_id}/feature-flags",
                json={"feature_key": "feature_inventada", "state": "active"},
            ),
            422,
            "feature fora do catalogo",
        )
        print("feature fora do catalogo: 422 OK")

        # 6) Remover a excecao devolve ao default.
        cleared = admin.delete(f"/organizations/{organization_id}/feature-flags/local_radar")
        assert_status(cleared, 200, "limpar excecao")
        radar = next(row for row in cleared.json() if row["feature_key"] == "local_radar")
        assert radar["is_override"] is False and radar["state"] == default_state("local_radar"), radar
        print("remover excecao volta ao default OK")
    finally:
        with connect() as conn:
            conn.execute("delete from organization_feature_flags where organization_id = %s", (workspace.organization_id,))
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_feature_flags passou")


if __name__ == "__main__":
    main()
