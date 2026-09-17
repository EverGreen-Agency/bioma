"""Smoke de AUTH-001 (convite por link) e feature-gating por organização.

Valida: criação de convite por EG admin, aceite público com criação de
usuário + sessão, isolamento do novo usuário, gates de módulo (analytics,
commercial, files) e uso único do token.
"""

from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.main import app


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
DEV_PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    admin = TestClient(app)
    invited = TestClient(app)
    anonymous = TestClient(app)

    assert_status(
        admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": DEV_PASSWORD}),
        200,
        "login admin",
    )

    clients = admin.get("/clients")
    assert_status(clients, 200, "listar clientes")
    client_id = next(row["id"] for row in clients.json() if row["organization_slug"] == "hm-conexoes")

    # Convite inválido não vaza nada.
    assert_status(anonymous.get("/auth/invites/token-invalido"), 404, "convite inválido")

    # Admin cria convite.
    created = admin.post(f"/clients/{client_id}/invites", json={})
    assert_status(created, 201, "criar convite")
    invite = created.json()
    assert invite["token"], "token do convite deveria vir na criação"
    assert invite["path"].startswith("/convite/"), "path do convite inesperado"

    listed = admin.get(f"/clients/{client_id}/invites")
    assert_status(listed, 200, "listar convites")
    assert any(row["id"] == invite["id"] for row in listed.json()), "convite criado deveria aparecer na lista"

    # Info pública do convite.
    info = anonymous.get(f"/auth/invites/{invite['token']}")
    assert_status(info, 200, "info pública do convite")
    assert info.json()["client_name"], "nome do cliente deveria aparecer no convite"

    # Aceite cria usuário + sessão.
    email = f"piloto-{uuid4().hex[:10]}@smoke.dev"
    accepted = invited.post(
        f"/auth/invites/{invite['token']}/accept",
        json={"display_name": "Piloto Smoke", "email": email, "password": "senha-piloto-123"},
    )
    assert_status(accepted, 200, "aceitar convite")
    accepted_user = accepted.json()["user"]
    roles = {org["role"] for org in accepted_user["organizations"]}
    assert roles == {"client_user"}, f"convidado deveria ser apenas client_user, veio {roles}"

    me = invited.get("/auth/me")
    assert_status(me, 200, "sessão do convidado ativa")

    # Senha curta é rejeitada em novo convite/aceite.
    weak = admin.post(f"/clients/{client_id}/invites", json={})
    assert_status(weak, 201, "criar convite para teste de senha")
    weak_accept = invited.post(
        f"/auth/invites/{weak.json()['token']}/accept",
        json={"display_name": "Fraco", "email": f"fraco-{uuid4().hex[:8]}@smoke.dev", "password": "curta"},
    )
    assert_status(weak_accept, 422, "senha curta deveria ser rejeitada")

    # Token é de uso único.
    reuse = anonymous.post(
        f"/auth/invites/{invite['token']}/accept",
        json={"display_name": "Reuso", "email": f"reuso-{uuid4().hex[:8]}@smoke.dev", "password": "senha-reuso-123"},
    )
    assert_status(reuse, 404, "reuso de convite deveria falhar")

    # Isolamento: convidado vê apenas o próprio cliente.
    invited_clients = invited.get("/clients")
    assert_status(invited_clients, 200, "clientes do convidado")
    ids = {row["id"] for row in invited_clients.json()}
    assert ids == {client_id}, f"convidado deveria ver só o próprio cliente, viu {ids}"

    # Gating default (hub/content/files): portal e arquivos ok; analytics e comercial 403.
    assert_status(invited.get(f"/clients/{client_id}"), 200, "portal (hub) liberado")
    assert_status(invited.get(f"/clients/{client_id}/files"), 200, "módulo files liberado")
    assert_status(invited.get(f"/clients/{client_id}/performance"), 403, "analytics bloqueado por default")
    assert_status(invited.get(f"/clients/{client_id}/leads"), 403, "comercial bloqueado por default")

    # Convidado não cria convite nem altera módulos.
    assert_status(invited.post(f"/clients/{client_id}/invites", json={}), 403, "client_user não convida")
    assert_status(
        invited.patch(f"/clients/{client_id}", json={"enabled_modules": ["hub", "analytics"]}),
        403,
        "client_user não altera módulos",
    )

    # Admin habilita analytics e o gate abre; depois reverte.
    enable = admin.patch(
        f"/clients/{client_id}",
        json={"enabled_modules": ["hub", "content", "files", "analytics"]},
    )
    assert_status(enable, 200, "habilitar módulo analytics")
    assert_status(invited.get(f"/clients/{client_id}/performance"), 200, "analytics liberado após toggle")

    unknown = admin.patch(f"/clients/{client_id}", json={"enabled_modules": ["hub", "hacker"]})
    assert_status(unknown, 422, "módulo desconhecido rejeitado")

    revert = admin.patch(
        f"/clients/{client_id}",
        json={"enabled_modules": ["hub", "content", "files"]},
    )
    assert_status(revert, 200, "reverter módulos ao default")
    assert_status(invited.get(f"/clients/{client_id}/performance"), 403, "analytics bloqueado após revert")

    print("smoke invites/gating ok")
    print(f"usuário convidado criado: {email}")


if __name__ == "__main__":
    main()
