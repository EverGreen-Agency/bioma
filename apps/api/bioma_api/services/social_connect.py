import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.config import get_settings
from bioma_api.crypto import encrypt_secret, require_encryption_configured
from bioma_api.repositories import performance as performance_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse

OAUTH_PROVIDERS = ("tiktok_organic", "tiktok_ads", "linkedin_organic")

# CRMs que autenticam por token estático por conta (não OAuth): o token é
# colado pelo operador e guardado cifrado, igual ao padrão do Kommo.
TOKEN_PROVIDERS = ("rd_station_crm", "hubspot")

TOKEN_PROVIDER_LABELS = {
    "rd_station_crm": "RD Station CRM",
    "hubspot": "HubSpot",
}


def save_provider_token(conn, client: dict, provider: str, token: str) -> UUID:
    """Grava o token de um CRM token-based, cifrado, numa performance_connection."""
    if provider not in TOKEN_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider não usa token estático.")
    require_encryption_configured()
    cleaned = token.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Token vazio.")

    label = TOKEN_PROVIDER_LABELS[provider]
    return performance_repo.create_connection(conn, client["id"], client["organization_id"], {
        "provider": provider,
        # Token-based não expõe um "account id" na autenticação; usamos o
        # próprio workspace como identificador estável da conexão, pra manter
        # o unique (client_id, provider, external_account_id) previsível.
        "external_account_id": str(client["workspace_id"]),
        "display_name": label,
        "status": "active",
        "metadata": {"api_token": encrypt_secret(cleaned)},
    })


def new_state() -> str:
    return secrets.token_urlsafe(24)


def resolve_client(conn, workspace_id: UUID, user: CurrentUserResponse) -> dict:
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "integrations")
    require_workspace_capability(client, user, "manage_config")
    return client


def build_authorize_url(provider: str, state: str, redirect_uri: str) -> str:
    settings = get_settings()
    if provider == "tiktok_organic":
        if not settings.tiktok_client_key:
            raise HTTPException(status_code=422, detail="TIKTOK_CLIENT_KEY não configurado no ambiente.")
        params = {
            "client_key": settings.tiktok_client_key,
            "response_type": "code",
            "scope": "user.info.basic,video.list",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}"

    if provider == "tiktok_ads":
        if not settings.tiktok_ads_app_id:
            raise HTTPException(status_code=422, detail="TIKTOK_ADS_APP_ID não configurado no ambiente.")
        params = {"app_id": settings.tiktok_ads_app_id, "state": state, "redirect_uri": redirect_uri}
        return f"https://business-api.tiktok.com/portal/auth?{urlencode(params)}"

    if provider == "linkedin_organic":
        if not settings.linkedin_client_id:
            raise HTTPException(status_code=422, detail="LINKEDIN_CLIENT_ID não configurado no ambiente.")
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "r_organization_social rw_organization_admin",
        }
        return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider OAuth não suportado.")


def exchange_code_and_save(conn, client: dict, provider: str, code: str, redirect_uri: str) -> list[UUID]:
    require_encryption_configured()
    settings = get_settings()
    if provider == "tiktok_organic":
        return _save_tiktok_organic(conn, client, code, redirect_uri, settings)
    if provider == "tiktok_ads":
        return _save_tiktok_ads(conn, client, code, redirect_uri, settings)
    if provider == "linkedin_organic":
        return _save_linkedin_organic(conn, client, code, redirect_uri, settings)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider OAuth não suportado.")


def _token_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    expires_in = payload.get("expires_in")
    expires_at = (
        (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
        if expires_in
        else None
    )
    return {
        "oauth_access_token": encrypt_secret(payload["access_token"]),
        "oauth_refresh_token": encrypt_secret(payload["refresh_token"]) if payload.get("refresh_token") else None,
        "oauth_expires_at": expires_at,
    }


def _save_tiktok_organic(conn, client: dict, code: str, redirect_uri: str, settings) -> list[UUID]:
    response = httpx.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise HTTPException(status_code=502, detail=f"TikTok: {payload.get('error_description', payload['error'])}")

    connection_id = performance_repo.create_connection(conn, client["id"], client["organization_id"], {
        "provider": "tiktok_organic",
        "external_account_id": payload["open_id"],
        "display_name": "TikTok (orgânico)",
        "status": "active",
        "metadata": _token_metadata(payload),
    })
    return [connection_id]


def _save_tiktok_ads(conn, client: dict, code: str, redirect_uri: str, settings) -> list[UUID]:
    response = httpx.post(
        "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/",
        json={"app_id": settings.tiktok_ads_app_id, "secret": settings.tiktok_ads_secret, "auth_code": code},
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (0, None):
        raise HTTPException(status_code=502, detail=f"TikTok Ads: {payload.get('message', 'erro desconhecido')}")

    data = payload.get("data") or {}
    advertiser_ids = data.get("advertiser_ids") or []
    if not advertiser_ids or not data.get("access_token"):
        raise HTTPException(status_code=502, detail="TikTok Ads não retornou advertiser_id/access_token autorizados.")

    access_token_encrypted = encrypt_secret(data["access_token"])
    connection_ids = []
    for advertiser_id in advertiser_ids:
        connection_id = performance_repo.create_connection(conn, client["id"], client["organization_id"], {
            "provider": "tiktok_ads",
            "external_account_id": str(advertiser_id),
            "display_name": f"TikTok Ads — {advertiser_id}",
            "status": "active",
            "metadata": {
                "oauth_access_token": access_token_encrypted,
                "oauth_refresh_token": None,
                "oauth_expires_at": None,
            },
        })
        connection_ids.append(connection_id)
    return connection_ids


def _save_linkedin_organic(conn, client: dict, code: str, redirect_uri: str, settings) -> list[UUID]:
    response = httpx.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise HTTPException(status_code=502, detail=f"LinkedIn: {payload.get('error_description', payload['error'])}")

    metadata = _token_metadata(payload)

    orgs_response = httpx.get(
        "https://api.linkedin.com/v2/organizationAcls",
        params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED"},
        headers={
            "Authorization": f"Bearer {payload['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        timeout=20,
    )
    orgs_response.raise_for_status()
    elements = orgs_response.json().get("elements", [])
    if not elements:
        raise HTTPException(
            status_code=502,
            detail="Nenhuma organização LinkedIn com papel de administrador encontrada para este login.",
        )

    connection_ids = []
    for element in elements:
        org_urn = element.get("organization")
        if not org_urn:
            continue
        connection_id = performance_repo.create_connection(conn, client["id"], client["organization_id"], {
            "provider": "linkedin_organic",
            "external_account_id": org_urn,
            "display_name": f"LinkedIn — {org_urn}",
            "status": "active",
            "metadata": metadata,
        })
        connection_ids.append(connection_id)
    return connection_ids
