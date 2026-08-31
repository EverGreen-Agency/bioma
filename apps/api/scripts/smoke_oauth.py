"""Smoke de AUTH-003: vínculo/desvínculo Google e login social.

O provedor Google é substituído por um fake (sem rede): o que se valida aqui
é o nosso lado do fluxo — state cookie, modos link/login, invite-only (login
social nunca cria conta), conflito de vínculo e desvinculação.
"""

import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Configura o OAuth ANTES de importar o app (settings é cacheado por processo).
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_ID", "smoke-client-id")
os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET", "smoke-client-secret")

from fastapi.testclient import TestClient

from bioma_api.main import app
from bioma_api.services import oauth as oauth_service


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
DEV_PASSWORD = "senha-dev-123"

FAKE_SUB = f"google-sub-{uuid4().hex[:12]}"
FAKE_EMAIL = f"admin-{uuid4().hex[:6]}@gmail.com"


def fake_fetch_google_user(code: str) -> dict:
    assert code == "smoke-code", f"código inesperado: {code}"
    return {"sub": FAKE_SUB, "email": FAKE_EMAIL, "email_verified": True, "name": "Admin Smoke"}


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def start_and_state(client: TestClient, mode: str) -> str:
    response = client.get(f"/auth/oauth/google/start?mode={mode}", follow_redirects=False)
    assert_status(response, 302, f"start {mode}")
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/"), f"redirect inesperado: {location}"
    return parse_qs(urlparse(location).query)["state"][0]


def main() -> None:
    oauth_service.fetch_google_user = fake_fetch_google_user
    import bioma_api.routers.oauth as oauth_router_module  # noqa: PLC0415

    assert oauth_router_module  # o router chama via oauth_service.fetch_google_user

    admin = TestClient(app)
    assert_status(
        admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": DEV_PASSWORD}),
        200,
        "login admin",
    )

    # Estado inicial: sem vínculos.
    identities = admin.get("/auth/identities")
    assert_status(identities, 200, "listar identities")
    for identity in identities.json():
        assert_status(admin.delete(f"/auth/identities/{identity['id']}"), 200, "limpar vínculo anterior")

    # Callback sem state válido é rejeitado.
    bad = admin.get("/auth/oauth/google/callback?code=x&state=forjado", follow_redirects=False)
    assert_status(bad, 302, "callback sem state")
    assert "oauth_error" in bad.headers["location"], "state inválido deveria redirecionar com erro"

    # LINK: admin logado vincula o Google.
    state = start_and_state(admin, "link")
    callback = admin.get(
        f"/auth/oauth/google/callback?code=smoke-code&state={state}",
        follow_redirects=False,
    )
    assert_status(callback, 302, "callback link")
    assert "linked=google" in callback.headers["location"], f"esperava linked=google: {callback.headers['location']}"

    identities = admin.get("/auth/identities").json()
    assert len(identities) == 1 and identities[0]["provider"] == "google", "vínculo não registrado"
    identity_id = identities[0]["id"]

    # Vincular de novo dá conflito explícito.
    state = start_and_state(admin, "link")
    conflict = admin.get(
        f"/auth/oauth/google/callback?code=smoke-code&state={state}",
        follow_redirects=False,
    )
    assert "oauth_error" in conflict.headers["location"], "segundo vínculo deveria falhar com erro"

    # LOGIN social: navegador novo, sem senha, entra pela conta vinculada.
    visitor = TestClient(app)
    state = start_and_state(visitor, "login")
    logged = visitor.get(
        f"/auth/oauth/google/callback?code=smoke-code&state={state}",
        follow_redirects=False,
    )
    assert_status(logged, 302, "callback login")
    assert "oauth_error" not in logged.headers["location"], f"login social falhou: {logged.headers['location']}"
    me = visitor.get("/auth/me")
    assert_status(me, 200, "sessão via Google ativa")
    assert me.json()["email"] == ADMIN_EMAIL, "logou no usuário errado"

    # Invite-only: sub desconhecido NÃO cria conta.
    unknown_sub = f"google-sub-desconhecido-{uuid4().hex[:8]}"

    def fake_unknown(code: str) -> dict:
        return {"sub": unknown_sub, "email": "estranho@gmail.com", "email_verified": True}

    oauth_service.fetch_google_user = fake_unknown
    stranger = TestClient(app)
    state = start_and_state(stranger, "login")
    denied = stranger.get(
        f"/auth/oauth/google/callback?code=smoke-code&state={state}",
        follow_redirects=False,
    )
    location = unquote(denied.headers["location"])
    assert "oauth_error" in location and "não está vinculada" in location, f"login de sub desconhecido deveria falhar: {location}"
    assert_status(stranger.get("/auth/me"), 401, "estranho não pode ter sessão")

    # UNLINK: desfaz o vínculo; login social volta a ser negado.
    oauth_service.fetch_google_user = fake_fetch_google_user
    unlinked = admin.delete(f"/auth/identities/{identity_id}")
    assert_status(unlinked, 200, "desvincular")
    assert unlinked.json() == [], "lista deveria ficar vazia"
    assert_status(admin.delete(f"/auth/identities/{identity_id}"), 404, "desvincular de novo é 404")

    visitor2 = TestClient(app)
    state = start_and_state(visitor2, "login")
    after = visitor2.get(
        f"/auth/oauth/google/callback?code=smoke-code&state={state}",
        follow_redirects=False,
    )
    assert "oauth_error" in after.headers["location"], "após desvincular, login social deveria ser negado"

    print("smoke oauth ok")


if __name__ == "__main__":
    main()
