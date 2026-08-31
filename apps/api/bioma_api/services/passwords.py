import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import passwords as passwords_repo
from bioma_api.schemas.auth import (
    CurrentUserResponse,
    PasswordChangeRequest,
    PasswordResetCreatedResponse,
    PasswordResetCreateRequest,
    PasswordResetPublicResponse,
)
from bioma_api.security import hash_password, hash_session_token, new_session_token, verify_password

RESET_TTL_HOURS = 2


def change_password(user: CurrentUserResponse, payload: PasswordChangeRequest, session_token: str) -> int:
    """Troca a senha do próprio usuário e revoga as demais sessões ativas."""
    with connect() as conn:
        row = passwords_repo.get_user(conn, user.id)
        if not row or not verify_password(payload.current_password, row["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha atual incorreta.")

        passwords_repo.set_password(conn, user.id, hash_password(payload.new_password))
        revoked = passwords_repo.revoke_sessions(conn, user.id, except_token_hash=hash_session_token(session_token))
        client_hub_repo.write_audit(
            conn,
            user.id,
            None,
            "auth.password_changed",
            {"revoked_sessions": revoked},
        )
    return revoked


def create_reset(payload: PasswordResetCreateRequest, admin: CurrentUserResponse) -> PasswordResetCreatedResponse:
    require_platform_admin(admin)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=RESET_TTL_HOURS)

    with connect() as conn:
        target = passwords_repo.find_user_by_email(conn, payload.email)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

        reset_id = passwords_repo.create_reset(conn, target["id"], hash_session_token(token), expires_at, admin.id)
        client_hub_repo.write_audit(
            conn,
            admin.id,
            None,
            "password_reset.created",
            {"reset_id": str(reset_id), "target_user_id": str(target["id"]), "email": target["email"]},
        )

    return PasswordResetCreatedResponse(
        id=reset_id,
        token=token,
        path=f"/redefinir/{token}",
        email=target["email"],
        expires_at=expires_at,
    )


def get_reset_public(token: str) -> PasswordResetPublicResponse:
    with connect() as conn:
        reset = passwords_repo.find_valid_reset(conn, hash_session_token(token))
    if not reset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link inválido, expirado ou já utilizado.")
    return PasswordResetPublicResponse(
        email_hint=_mask_email(reset["email"]),
        display_name=reset["display_name"],
        expires_at=reset["expires_at"],
    )


def confirm_reset(token: str, password: str) -> tuple[str, datetime]:
    """Define a nova senha, revoga todas as sessões antigas e abre sessão nova.

    Retorna (session_token, expires_at) para o router setar o cookie.
    """
    settings = get_settings()
    with connect() as conn:
        reset = passwords_repo.find_valid_reset(conn, hash_session_token(token))
        if not reset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link inválido, expirado ou já utilizado.")

        passwords_repo.set_password(conn, reset["user_id"], hash_password(password))
        passwords_repo.mark_reset_used(conn, reset["id"])
        revoked = passwords_repo.revoke_sessions(conn, reset["user_id"])

        session_token = new_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
        passwords_repo.create_session(conn, reset["user_id"], hash_session_token(session_token), expires_at)

        client_hub_repo.write_audit(
            conn,
            reset["user_id"],
            None,
            "password_reset.used",
            {"reset_id": str(reset["id"]), "revoked_sessions": revoked},
        )

    return session_token, expires_at


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    visible = local[:1] if local else ""
    return f"{visible}•••@{domain}"
