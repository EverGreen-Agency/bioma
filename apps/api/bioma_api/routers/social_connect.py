from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from bioma_api.auth import current_user_from_request
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.performance import PerformanceConnectionSummary
from bioma_api.services import performance as performance_service
from bioma_api.services import social_connect as service

router = APIRouter(tags=["social-connect"])


class ProviderTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2000)

STATE_COOKIE = "bioma_social_oauth_state"


def _redirect_uri(provider: str) -> str:
    return f"{get_settings().api_public_url.rstrip('/')}/integrations/social-connect/{provider}/callback"


def _client_redirect(client_id: UUID, error: str | None = None) -> RedirectResponse:
    base = get_settings().web_app_url.rstrip("/")
    url = f"{base}/clientes/{client_id}/integracoes"
    if error:
        url = f"{url}?oauth_error={error}"
    return RedirectResponse(url, status_code=302)


@router.get("/workspaces/{workspace_id}/performance/connections/{provider}/authorize")
def authorize(
    workspace_id: UUID,
    provider: str,
    request: Request,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> RedirectResponse:
    if provider not in service.OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="Provider OAuth não suportado.")
    with connect() as conn:
        client = service.resolve_client(conn, workspace_id, user)

    state = service.new_state()
    authorize_url = service.build_authorize_url(provider, state, _redirect_uri(provider))
    response = RedirectResponse(authorize_url, status_code=302)
    settings = get_settings()
    response.set_cookie(
        key=STATE_COOKIE,
        value=f"{state}:{client['id']}:{provider}",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=600,
        path="/integrations/social-connect",
    )
    return response


@router.put(
    "/workspaces/{workspace_id}/performance/connections/{provider}/token",
    response_model=list[PerformanceConnectionSummary],
)
def save_provider_token(
    workspace_id: UUID,
    provider: str,
    payload: ProviderTokenRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[PerformanceConnectionSummary]:
    """Salva o token de um CRM token-based (RD Station, HubSpot), cifrado.

    O token nunca volta na resposta: a listagem devolve só o estado da conexão.
    """
    if provider not in service.TOKEN_PROVIDERS:
        raise HTTPException(status_code=404, detail="Provider não usa token estático.")
    with connect() as conn:
        client = service.resolve_client(conn, workspace_id, user)
        service.save_provider_token(conn, client, provider, payload.token)
    return performance_service.list_connections(workspace_id, user)


@router.get("/integrations/social-connect/{provider}/callback")
def callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> RedirectResponse:
    stored = request.cookies.get(STATE_COOKIE, "")
    stored_state, _, rest = stored.partition(":")
    stored_client_id, _, stored_provider = rest.partition(":")

    if error or not code or not state or state != stored_state or provider != stored_provider or not stored_client_id:
        # Sem client_id resolvido ainda (cookie ausente/adulterado): não dá pra
        # redirecionar de volta pra aba do cliente com segurança.
        response = RedirectResponse(f"{get_settings().web_app_url.rstrip('/')}/", status_code=302)
        response.delete_cookie(STATE_COOKIE, path="/integrations/social-connect")
        return response

    client_id = UUID(stored_client_id)
    try:
        with connect() as conn:
            client = service.resolve_client(conn, client_id, user)
            service.exchange_code_and_save(conn, client, provider, code, _redirect_uri(provider))
    except HTTPException as exc:
        response = _client_redirect(client_id, error=str(exc.detail))
        response.delete_cookie(STATE_COOKIE, path="/integrations/social-connect")
        return response

    response = _client_redirect(client_id)
    response.delete_cookie(STATE_COOKIE, path="/integrations/social-connect")
    return response
