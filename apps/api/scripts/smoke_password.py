"""Smoke de AUTH-002: reset de senha por link e rotação de senha logado.

Valida: admin gera link para usuário existente, confirmação define nova
senha + revoga sessões antigas + loga o usuário, token é de uso único,
troca de senha logado exige senha atual e revoga as demais sessões.
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
    assert_status(
        admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": DEV_PASSWORD}),
        200,
        "login admin",
    )

    # Usuário alvo: convidado novo, para não mexer na senha do seed.
    clients = admin.get("/clients")
    assert_status(clients, 200, "listar clientes")
    client_id = next(row["id"] for row in clients.json() if row["organization_slug"] == "hm-conexoes")

    invite = admin.post(f"/clients/{client_id}/invites", json={})
    assert_status(invite, 201, "criar convite")

    target_email = f"reset-{uuid4().hex[:10]}@smoke.dev"
    first_password = "senha-inicial-123"
    target = TestClient(app)
    assert_status(
        target.post(
            f"/auth/invites/{invite.json()['token']}/accept",
            json={"display_name": "Alvo Reset", "email": target_email, "password": first_password},
        ),
        200,
        "aceitar convite",
    )
    assert_status(target.get("/auth/me"), 200, "sessão inicial ativa")

    # client_user não gera reset.
    assert_status(
        target.post("/auth/password-resets", json={"email": target_email}),
        403,
        "client_user não gera reset",
    )

    # E-mail inexistente: 404 (endpoint é admin-only, sem risco de enumeração pública).
    assert_status(
        admin.post("/auth/password-resets", json={"email": "nao-existe@smoke.dev"}),
        404,
        "reset para e-mail inexistente",
    )

    # Admin gera o link.
    reset = admin.post("/auth/password-resets", json={"email": target_email})
    assert_status(reset, 201, "admin gera reset")
    token = reset.json()["token"]
    assert reset.json()["path"].startswith("/redefinir/"), "path do reset inesperado"

    # Info pública mascara o e-mail.
    info = TestClient(app).get(f"/auth/password-resets/{token}")
    assert_status(info, 200, "info pública do reset")
    assert "•••" in info.json()["email_hint"], "e-mail deveria vir mascarado"
    assert target_email not in info.json()["email_hint"], "e-mail completo não deve vazar"

    # Confirmação: nova senha, sessões antigas revogadas, sessão nova aberta.
    new_password = "senha-nova-456"
    fresh = TestClient(app)
    confirmed = fresh.post(f"/auth/password-resets/{token}/confirm", json={"password": new_password})
    assert_status(confirmed, 200, "confirmar reset")
    assert_status(fresh.get("/auth/me"), 200, "sessão nova do reset ativa")
    assert_status(target.get("/auth/me"), 401, "sessão antiga revogada pelo reset")

    # Token de uso único.
    assert_status(
        TestClient(app).post(f"/auth/password-resets/{token}/confirm", json={"password": "outra-senha-789"}),
        404,
        "reuso do reset deveria falhar",
    )

    # Senha antiga morta, nova funciona.
    assert_status(
        TestClient(app).post("/auth/login", json={"email": target_email, "password": first_password}),
        401,
        "senha antiga não loga",
    )
    relogin = TestClient(app)
    assert_status(
        relogin.post("/auth/login", json={"email": target_email, "password": new_password}),
        200,
        "senha nova loga",
    )

    # Rotação logado: senha atual errada falha; certa troca e revoga a outra sessão.
    assert_status(
        relogin.post("/auth/password", json={"current_password": "errada-123", "new_password": "senha-final-789"}),
        401,
        "senha atual errada",
    )
    change = relogin.post(
        "/auth/password",
        json={"current_password": new_password, "new_password": "senha-final-789"},
    )
    assert_status(change, 200, "trocar senha logado")
    assert change.json()["revoked_sessions"] >= 1, "sessão paralela deveria ser revogada"
    assert_status(relogin.get("/auth/me"), 200, "sessão atual sobrevive à troca")
    assert_status(fresh.get("/auth/me"), 401, "sessão paralela revogada pela troca")

    print("smoke password ok")
    print(f"usuário de teste: {target_email}")


if __name__ == "__main__":
    main()
