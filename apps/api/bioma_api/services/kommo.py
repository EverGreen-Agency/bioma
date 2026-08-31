"""Bridge Kommo (decisão 2026-07-10: espelho do funil, padrão ClickUp Bridge).

Segurança: client_secret/access_token/refresh_token só entram no banco
cifrados (Fernet, `bioma_api.crypto`) e nunca voltam em resposta HTTP —
o GET expõe apenas subdomain. Para `client_user`, tudo fica atrás do
módulo `commercial` (feature-gating por organização).
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.crypto import encrypt_secret, require_encryption_configured
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import kommo as kommo_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse


def _require_access_and_module(conn, user: CurrentUserResponse, organization_id: UUID):
    org = workspaces_repo.find_accessible_organization(
        conn,
        organization_id,
        is_platform_admin(user),
        user.id,
    )
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organização não encontrada.")
    if is_platform_admin(user):
        return org
    require_client_module(org, user, "commercial")
    return org


def get_config(user: CurrentUserResponse, organization_id: UUID) -> dict:
    with connect() as conn:
        _require_access_and_module(conn, user, organization_id)
        row = kommo_repo.get_config_public(conn, organization_id)
    if row:
        return {"configured": True, "subdomain": row["subdomain"]}
    return {"configured": False, "subdomain": None}


def save_config(
    user: CurrentUserResponse,
    organization_id: UUID,
    client_id: str,
    client_secret: str,
    access_token: str,
    subdomain: str,
) -> None:
    require_encryption_configured()

    subdomain = subdomain.strip().lower()
    if not subdomain or not client_id.strip() or not client_secret.strip() or not access_token.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Subdomínio, client id, client secret e access token são obrigatórios.",
        )

    with connect() as conn:
        org = _require_access_and_module(conn, user, organization_id)
        require_workspace_capability(org, user, "manage_config")
        kommo_repo.upsert_integration(
            conn,
            organization_id,
            client_id.strip(),
            encrypt_secret(client_secret.strip()),
            encrypt_secret(access_token.strip()),
            subdomain,
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "kommo.config_saved",
            {"subdomain": subdomain},
        )


def get_metrics(user: CurrentUserResponse, organization_id: UUID) -> list[dict]:
    with connect() as conn:
        _require_access_and_module(conn, user, organization_id)
        rows = kommo_repo.latest_metrics(conn, organization_id)
    return [dict(row) for row in rows]
