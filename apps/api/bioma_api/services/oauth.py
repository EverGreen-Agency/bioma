"""Login social como vínculo (AUTH-003, decisão 2026-07-16).

Modelo: a conta do Bioma é sempre o usuário convidado pela EG; o Google é uma
identidade que o usuário logado VINCULA (e pode DESVINCULAR a qualquer
momento) para facilitar logins futuros. O "Entrar com Google" só funciona
para quem já vinculou — nunca cria conta (o Bioma é invite-only) e nunca
prende a conta ao Google (a senha continua existindo como método próprio).

Fluxo técnico: Authorization Code (cliente confidencial) + userinfo endpoint.
Não verificamos o id_token localmente porque o access_token vem direto do
Google via TLS na troca do código — o userinfo é a fonte da identidade.
"""

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import identities as identities_repo
from bioma_api.repositories import passwords as passwords_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.security import hash_session_token, new_session_token

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def redirect_uri() -> str:
    return f"{get_settings().api_public_url.rstrip('/')}/auth/oauth/google/callback"


def build_authorize_url(state: str) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def fetch_google_user(code: str) -> dict:
    """Troca o código por tokens e retorna o userinfo (sub/email/nome).

    Mantida como função de módulo para o smoke poder substituí-la por um
    provedor falso sem rede.
    """
    settings = get_settings()
    with httpx.Client(timeout=15) as http:
        token_response = http.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível validar o código do Google.",
            )
        access_token = token_response.json().get("access_token")
        userinfo_response = http.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível obter o perfil Google.",
            )
    return userinfo_response.json()


def link_google(user: CurrentUserResponse, google_user: dict) -> None:
    subject = google_user.get("sub")
    email = google_user.get("email")
    if not subject:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Perfil Google sem identificador.")

    with connect() as conn:
        existing = identities_repo.find_by_subject(conn, "google", subject)
        if existing and existing["user_id"] != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta conta Google já está vinculada a outro usuário.",
            )
        if identities_repo.find_for_user_by_provider(conn, user.id, "google"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Você já tem uma conta Google vinculada. Desvincule antes de trocar.",
            )
        identity_id = identities_repo.create(conn, user.id, "google", subject, email)
        client_hub_repo.write_audit(
            conn,
            user.id,
            None,
            "identity.linked",
            {"identity_id": str(identity_id), "provider": "google", "email": email},
        )


def login_with_google(google_user: dict) -> tuple[str, datetime]:
    """Sessão para usuário com Google já vinculado; nunca cria conta."""
    settings = get_settings()
    subject = google_user.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Perfil Google sem identificador.")

    with connect() as conn:
        identity = identities_repo.find_by_subject(conn, "google", subject)
        if not identity or not identity["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Esta conta Google não está vinculada a nenhum acesso do Bioma. Entre com e-mail e senha e vincule em Configurações.",
            )

        session_token = new_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
        passwords_repo.create_session(conn, identity["user_id"], hash_session_token(session_token), expires_at)
        client_hub_repo.write_audit(
            conn,
            identity["user_id"],
            None,
            "auth.login_google",
            {"identity_id": str(identity["id"])},
        )

    return session_token, expires_at


def list_identities(user: CurrentUserResponse):
    with connect() as conn:
        return identities_repo.list_for_user(conn, user.id)


def unlink_identity(user: CurrentUserResponse, identity_id: UUID):
    with connect() as conn:
        # Nunca deixar a conta sem método de login próprio: como o Bioma cria
        # toda conta com senha (convite/bootstrap), a checagem é uma garantia
        # contra futuros fluxos sem senha.
        if not identities_repo.user_has_password(conn, user.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Defina uma senha antes de desvincular o único método de login.",
            )
        if not identities_repo.delete(conn, user.id, identity_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vínculo não encontrado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            None,
            "identity.unlinked",
            {"identity_id": str(identity_id), "provider": "google"},
        )
        return identities_repo.list_for_user(conn, user.id)


def new_state() -> str:
    return secrets.token_urlsafe(24)
