import sys
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.crypto import decrypt_secret, encrypt_secret, require_encryption_configured
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import whatsapp as wa_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.whatsapp import (
    WhatsAppMessageLogSummary,
    WhatsAppProviderConfigPayload,
    WhatsAppProviderConfigSummary,
    WhatsAppSendMessagePayload,
)
from bioma_api.worker_bridge import get_whatsapp_provider_safe


def list_providers(workspace_id: UUID, user: CurrentUserResponse) -> list[WhatsAppProviderConfigSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = wa_repo.list_provider_configs(conn, client["workspace_id"])
    return [WhatsAppProviderConfigSummary(**row) for row in rows]


def upsert_provider(
    workspace_id: UUID,
    payload: WhatsAppProviderConfigPayload,
    user: CurrentUserResponse,
) -> WhatsAppProviderConfigSummary:
    data = payload.model_dump()
    if data.get("api_token"):
        require_encryption_configured()
        data["api_token"] = encrypt_secret(data["api_token"].strip())
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user, "manage_config")
        row = wa_repo.upsert_provider_config(conn, client["workspace_id"], data)
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "whatsapp.provider_configured",
            {
                "workspace_id": str(client["workspace_id"]),
                "provider_type": payload.provider_type,
                "status": payload.status,
            },
        )
    return WhatsAppProviderConfigSummary(**row)


def send_message(
    workspace_id: UUID,
    payload: WhatsAppSendMessagePayload,
    user: CurrentUserResponse,
) -> WhatsAppMessageLogSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user, "manage_work")
        config_row = wa_repo.get_provider_config(conn, client["workspace_id"], payload.provider_type)

        config_dict = dict(config_row) if config_row else {"provider_type": payload.provider_type}
        if config_dict.get("api_token"):
            config_dict["api_token"] = decrypt_secret(config_dict["api_token"])
        provider = get_whatsapp_provider_safe(payload.provider_type, config_dict)

        if payload.template_name:
            res = provider.send_template_message(payload.to_number, payload.template_name, payload.template_variables)
            msg_type = "template"
        else:
            res = provider.send_text_message(payload.to_number, payload.message_text)
            msg_type = "text"

        log_row = wa_repo.log_message(
            conn,
            client["workspace_id"],
            {
                "provider_type": payload.provider_type,
                "to_number": payload.to_number,
                "message_type": msg_type,
                "payload": res,
                "status": "sent" if res.get("status") in ["sent", "simulated"] else "failed",
                "error_message": res.get("error"),
            },
        )
    return WhatsAppMessageLogSummary(**log_row)


def list_logs(workspace_id: UUID, user: CurrentUserResponse, limit: int = 50) -> list[WhatsAppMessageLogSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = wa_repo.list_logs(conn, client["workspace_id"], limit)
    return [WhatsAppMessageLogSummary(**row) for row in rows]


def _accessible_workspace(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "integrations")
    if capability:
        require_workspace_capability(client, user, capability)
    return client
