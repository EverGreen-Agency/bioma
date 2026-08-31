from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
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

    suffix = uuid4().hex[:8]
    created = admin.post(
        "/clients",
        json={
            "name": f"Smoke Files {suffix}",
            "organization_name": f"Smoke Files Org {suffix}",
            "status": "active",
        },
    )
    assert_status(created, 201, "create client for files smoke")
    client_id = created.json()["client"]["id"]
    org_id = created.json()["client"]["organization_id"]

    empty_list = admin.get(f"/clients/{client_id}/files")
    assert_status(empty_list, 200, "list files empty")
    assert empty_list.json() == [], "novo cliente não deveria ter arquivos"

    client_forbidden_upload = client_user.post(
        f"/clients/{client_id}/files",
        files={"file": ("nao-autorizado.txt", b"conteudo", "text/plain")},
        data={"visibility": "client"},
    )
    assert client_forbidden_upload.status_code in (403, 404), "client_user não deve conseguir subir arquivo de outro cliente"

    client_content = b"Documento visivel para o cliente HM."
    client_upload = admin.post(
        f"/clients/{client_id}/files",
        files={"file": ("proposta-cliente.txt", client_content, "text/plain")},
        data={"visibility": "client"},
    )
    assert_status(client_upload, 201, "upload arquivo visibility=client")

    internal_upload = admin.post(
        f"/clients/{client_id}/files",
        files={"file": ("nota-interna.txt", b"Somente EG deve ver isso.", "text/plain")},
        data={"visibility": "internal"},
    )
    assert_status(internal_upload, 201, "upload arquivo visibility=internal")

    admin_files = admin.get(f"/clients/{client_id}/files").json()
    assert len(admin_files) == 2, "admin deve ver os dois arquivos"

    client_files = client_user.get(f"/clients/{client_id}/files")
    assert_status(client_files, 404, "client_user não acessa outro cliente (organização diferente no seed)")

    client_visible_file_id = next(item["id"] for item in admin_files if item["visibility"] == "client")
    internal_file_id = next(item["id"] for item in admin_files if item["visibility"] == "internal")

    download = admin.get(f"/clients/{client_id}/files/{client_visible_file_id}/download")
    assert_status(download, 200, "gerar link de download")
    download_url = download.json()["url"]
    fetched = httpx.get(download_url, timeout=10)
    assert fetched.status_code == 200, f"download do arquivo via URL assinada falhou: {fetched.status_code}"
    assert fetched.content == client_content, "conteúdo baixado difere do conteúdo enviado"

    oversized = admin.post(
        f"/clients/{client_id}/files",
        files={"file": ("grande.bin", b"0" * (21 * 1024 * 1024), "application/octet-stream")},
        data={"visibility": "client"},
    )
    assert_status(oversized, 413, "upload acima do limite deve ser rejeitado")

    deleted = admin.delete(f"/clients/{client_id}/files/{internal_file_id}")
    assert_status(deleted, 200, "excluir arquivo interno")
    remaining = admin.get(f"/clients/{client_id}/files").json()
    assert len(remaining) == 1, "deveria restar 1 arquivo após exclusão"

    with connect() as conn:
        conn.execute("delete from organizations where id = %s", (org_id,))

    print("smoke files ok")


if __name__ == "__main__":
    main()
