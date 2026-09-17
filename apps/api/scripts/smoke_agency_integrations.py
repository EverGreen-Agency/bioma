"""Smoke do dogfooding de métricas: a EG mede a própria mídia.

Por que existe: a Operação EG é um workspace SEM registro em `clients` — a
agência não tem contrato consigo mesma. Esse é o único caminho da aplicação em
que o contexto resolve sem cliente, e nenhuma tela de cliente o exercita, então
é exatamente o tipo de caminho que quebra sem ninguém perceber.

Até 2026-08-07 existia um cliente "EverGreen Internal" só para preencher
`performance_connections.client_id` (NOT NULL até a 0087) e para o resolvedor,
que partia de `clients`. As duas restrições caíram; o registro-fantasma sumiu.

Valida:
- o workspace da EG resolve pelo mesmo gate dos clientes, SEM registro em
  `clients`, e a conexão criada fica com `client_id` nulo;
- dá para cadastrar a conta de mídia da EG (o vínculo com o MCC/BM vive em
  `external_parent_id`, separado da credencial, que é do ambiente);
- a conexão da EG **não vaza** para a listagem de um cliente e vice-versa;
- usuário de cliente não alcança o workspace interno nem o estado do ambiente.

NÃO valida chamada real ao Google/Meta — isso depende de credencial externa e
está fora do alcance de um smoke.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-agency-integrations-client@bioma.example.com"
PASSWORD = "senha-dev-123"

# Conta fictícia mas inconfundível: se aparecer numa tela, é resíduo de smoke.
SMOKE_ACCOUNT_ID = "smoke-eg-000000"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def find_agency_workspace(conn):
    """O sujeito interno da EG e o WORKSPACE, nao um registro em `clients`.

    Ate 2026-08-07 este smoke buscava um cliente "EverGreen Internal". Ele
    existia so para satisfazer restricoes que a 0087 removeu."""
    return conn.execute(
        "select id from workspaces where kind = 'agency_internal' and status = 'active' limit 1"
    ).fetchone()


def main() -> None:
    with connect() as conn:
        internal = find_agency_workspace(conn)
    if not internal:
        raise AssertionError(
            "Workspace interno da EG não existe. Rode scripts/create_eg_client.py."
        )
    agency_workspace_id = internal["id"]

    workspace = create_smoke_workspace("AGENCYINT")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Smoke Cliente Integrações", PASSWORD)
    grant_client_user(workspace, client_user_id)
    atexit.register(cleanup_smoke_data, [workspace.organization_id], [CLIENT_EMAIL])

    try:
        admin = TestClient(app)
        assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")

        # ---------------------------------------------------------------- 1
        response = admin.get(f"/clients/{agency_workspace_id}/performance/connections")
        assert_status(response, 200, "listar conexões da EG")
        print(f"ok: workspace da EG resolve sem registro de cliente ({len(response.json())} conexões)")

        # ---------------------------------------------------------------- 2
        # Cadastrar a conta da EG, com o MCC no external_parent_id.
        response = admin.post(
            f"/clients/{agency_workspace_id}/performance/connections",
            json={
                "provider": "google_ads",
                "external_account_id": SMOKE_ACCOUNT_ID,
                "external_parent_id": "smoke-mcc-000000",
                "display_name": "Smoke EG Ads",
            },
        )
        assert_status(response, 201, "criar conexão da EG")
        created = [item for item in response.json() if item["external_account_id"] == SMOKE_ACCOUNT_ID]
        if not created:
            raise AssertionError("conexão criada não voltou na listagem")
        if created[0]["client_id"] is not None:
            raise AssertionError(
                f"conexão da agência nasceu amarrada a um cliente: {created[0]['client_id']}"
            )
        if created[0]["external_parent_id"] != "smoke-mcc-000000":
            raise AssertionError("o vínculo com o MCC não foi preservado")
        print("ok: conta da EG cadastrada com o MCC em external_parent_id (credencial fica no ambiente)")

        # ---------------------------------------------------------------- 3
        # Isolamento: a conta da EG não pode aparecer na listagem do cliente.
        response = admin.get(f"/clients/{workspace.client_id}/performance/connections")
        assert_status(response, 200, "listar conexões do cliente")
        if any(item["external_account_id"] == SMOKE_ACCOUNT_ID for item in response.json()):
            raise AssertionError("a conexão da EG vazou para a listagem de um cliente")
        print("ok: conexão da EG não vaza para a carteira de cliente")

        # ---------------------------------------------------------------- 4
        # Usuário de cliente não alcança o registro interno da EG. 404 (não
        # 403) porque não se confirma a existência do que não é dele.
        cliente = TestClient(app)
        assert_status(cliente.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")
        response = cliente.get(f"/clients/{agency_workspace_id}/performance/connections")
        if response.status_code not in (403, 404):
            raise AssertionError(f"cliente alcançou o workspace interno da EG: {response.status_code}")
        print(f"ok: usuário de cliente não alcança o workspace interno da EG ({response.status_code})")

        # ---------------------------------------------------------------- 5
        # A tela mora em Configurações → Empresa → Integrações, que é EG-only
        # pelo próprio `isEgAdmin`. O que precisa continuar valendo é o gate da
        # API: cliente não lê o estado de credenciais do ambiente.
        response = cliente.get("/integrations/status")
        if response.status_code not in (403, 404):
            raise AssertionError(f"cliente leu o estado do ambiente: {response.status_code}")
        print(f"ok: estado do ambiente é EG-only ({response.status_code})")

        print("\nSMOKE AGENCY INTEGRATIONS: OK")
    finally:
        with connect() as conn:
            conn.execute(
                "delete from performance_connections where external_account_id = %s",
                (SMOKE_ACCOUNT_ID,),
            )
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])


if __name__ == "__main__":
    main()
