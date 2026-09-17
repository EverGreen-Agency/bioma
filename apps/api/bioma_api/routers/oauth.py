from datetime import datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from bioma_api.auth import current_user_from_request, session_cookie_kwargs
from bioma_api.config import get_settings
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services import oauth as oauth_service

router = APIRouter(prefix="/auth", tags=["oauth"])

STATE_COOKIE = "bioma_oauth_state"


class IdentitySummary(BaseModel):
    id: UUID
    provider: str
    email: str | None = None
    created_at: datetime


def _web_redirect(path: str, error: str | None = None) -> RedirectResponse:
    base = get_settings().web_app_url.rstrip("/")
    url = f"{base}{path}"
    if error:
        separator = "&" if "?" in path else "?"
        url = f"{url}{separator}oauth_error={quote(error)}"
    return RedirectResponse(url, status_code=302)


def _state_cookie_kwargs() -> dict:
    settings = get_settings()
    return {
        "key": STATE_COOKIE,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "max_age": 600,
        "path": "/auth/oauth",
    }


@router.get("/oauth/google/start")
def google_start(mode: str = "login") -> RedirectResponse:
    settings = get_settings()
    if mode not in ("login", "link"):
        mode = "login"
    if not settings.google_oauth_configured:
        return _web_redirect("/", error="Login com Google ainda não está configurado neste ambiente.")

    state = oauth_service.new_state()
    response = RedirectResponse(oauth_service.build_authorize_url(state), status_code=302)
    response.set_cookie(value=f"{state}:{mode}", **_state_cookie_kwargs())
    return response


@router.get("/oauth/google/callback")
def google_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    settings = get_settings()
    if not settings.google_oauth_configured:
        return _web_redirect("/", error="Login com Google não está configurado.")

    stored = request.cookies.get(STATE_COOKIE, "")
    stored_state, _, mode = stored.partition(":")
    if error or not code or not state or not stored_state or state != stored_state:
        response = _web_redirect("/", error="Autorização Google cancelada ou inválida. Tente novamente.")
        response.delete_cookie(STATE_COOKIE, path="/auth/oauth")
        return response

    try:
        google_user = oauth_service.fetch_google_user(code)
    except HTTPException as exc:
        response = _web_redirect("/", error=str(exc.detail))
        response.delete_cookie(STATE_COOKIE, path="/auth/oauth")
        return response

    if mode == "link":
        try:
            user = current_user_from_request(request)
        except HTTPException:
            response = _web_redirect("/", error="Sessão expirada. Entre novamente e vincule o Google em Configurações.")
            response.delete_cookie(STATE_COOKIE, path="/auth/oauth")
            return response
        try:
            oauth_service.link_google(user, google_user)
        except HTTPException as exc:
            response = _web_redirect("/configuracoes", error=str(exc.detail))
            response.delete_cookie(STATE_COOKIE, path="/auth/oauth")
            return response
        response = _web_redirect("/configuracoes?linked=google")
        response.delete_cookie(STATE_COOKIE, path="/auth/oauth")
        return response

    # mode == "login"
    try:
        session_token, expires_at = oauth_service.login_with_google(google_user)
    except HTTPException as exc:
        response = _web_redirect("/", error=str(exc.detail))
        response.delete_cookie(STATE_COOKIE, path="/auth/oauth")
        return response

    response = _web_redirect("/")
    response.set_cookie(value=session_token, **session_cookie_kwargs(expires_at))
    response.delete_cookie(STATE_COOKIE, path="/auth/oauth")
    return response


@router.get("/identities", response_model=list[IdentitySummary])
def list_identities(user: CurrentUserResponse = Depends(current_user_from_request)) -> list[IdentitySummary]:
    return [IdentitySummary(**row) for row in oauth_service.list_identities(user)]


@router.delete("/identities/{identity_id}", response_model=list[IdentitySummary])
def unlink_identity(
    identity_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[IdentitySummary]:
    return [IdentitySummary(**row) for row in oauth_service.unlink_identity(user, identity_id)]
