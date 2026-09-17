"""Smoke da bridge Kommo: cifra em repouso, gates de acesso e métricas.

Valida: anônimo 401; client_user sem módulo commercial 403; admin salva
config e os segredos vão pro banco CIFRADOS (nunca plaintext); GET expõe
só o subdomain; métricas respondem vazio sem snapshot; client_user com
módulo commercial habilitado passa a ler config/métricas.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Chave de cifra ANTES de importar o app (settings é cacheado por processo).
os.environ.setdefault(
    "SECRET_ENCRYPTION_KEY",
    __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode(),
)

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "henrique@hmconexoes.com.br"
DEV_PASSWORD = "senha-dev-123"

SECRET_VALUE = "segredo-super-sensivel-123"
TOKEN_VALUE = "token-super-sensivel-456"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    admin = TestClient(app)
    client_user = TestClient(app)
    anon = TestClient(app)

    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": DEV_PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": DEV_PASSWORD}), 200, "login cliente")

    clients = admin.get("/clients").json()
    hm = next(c for c in clients if c["organization_slug"] == "hm-conexoes")
    org_id = hm["organization_id"]

    # Anônimo e UUID inválido
    assert_status(anon.get(f"/integrations/{org_id}/kommo"), 401, "config anônimo")
    assert_status(admin.get("/integrations/nao-uuid/kommo"), 422, "uuid inválido")

    # client_user sem módulo commercial (default): 403
    assert_status(client_user.get(f"/integrations/{org_id}/kommo"), 403, "config cliente sem módulo commercial")
    assert_status(client_user.get(f"/analytics/{org_id}/kommo"), 403, "métricas cliente sem módulo commercial")

    # client_user não grava config
    assert_status(
        client_user.post(
            f"/integrations/{org_id}/kommo",
            json={"client_id": "x", "client_secret": "y", "access_token": "z", "subdomain": "hm"},
        ),
        403,
        "cliente não grava config",
    )

    # Admin salva; segredos precisam ir cifrados pro banco
    assert_status(
        admin.post(
            f"/integrations/{org_id}/kommo",
            json={
                "client_id": "kommo-client-id",
                "client_secret": SECRET_VALUE,
                "access_token": TOKEN_VALUE,
                "subdomain": "evergreen",
            },
        ),
        200,
        "admin salva config",
    )

    with connect() as conn:
        row = conn.execute(
            "select client_secret, access_token from kommo_integrations where organization_id = %s",
            (org_id,),
        ).fetchone()
    assert row, "config não foi gravada"
    assert row["client_secret"].startswith("enc:v1:"), "client_secret deveria estar cifrado"
    assert row["access_token"].startswith("enc:v1:"), "access_token deveria estar cifrado"
    assert SECRET_VALUE not in row["client_secret"], "client_secret vazou em texto puro"
    assert TOKEN_VALUE not in row["access_token"], "access_token vazou em texto puro"

    # GET só expõe subdomain
    config = admin.get(f"/integrations/{org_id}/kommo")
    assert_status(config, 200, "config admin")
    body = config.json()
    assert body == {"configured": True, "subdomain": "evergreen"}, f"resposta inesperada: {body}"

    # Métricas: sem snapshot ainda, lista vazia
    metrics = admin.get(f"/analytics/{org_id}/kommo")
    assert_status(metrics, 200, "métricas admin")
    assert metrics.json() == {"pipelines": []}, "esperava pipelines vazios sem snapshot"

    # Habilitando o módulo commercial, o cliente passa a ler
    assert_status(
        admin.patch(f"/clients/{hm['id']}", json={"enabled_modules": ["hub", "content", "files", "commercial"]}),
        200,
        "habilitar commercial",
    )
    assert_status(client_user.get(f"/integrations/{org_id}/kommo"), 200, "config cliente com módulo")
    assert_status(client_user.get(f"/analytics/{org_id}/kommo"), 200, "métricas cliente com módulo")

    # Reverte módulos e remove a config de teste
    assert_status(
        admin.patch(f"/clients/{hm['id']}", json={"enabled_modules": ["hub", "content", "files"]}),
        200,
        "reverter módulos",
    )
    with connect() as conn:
        conn.execute("delete from kommo_integrations where organization_id = %s", (org_id,))

    print("smoke kommo ok")


if __name__ == "__main__":
    main()
