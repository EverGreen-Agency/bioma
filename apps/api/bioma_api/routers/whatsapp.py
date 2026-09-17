from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.whatsapp import (
    WhatsAppMessageLogSummary,
    WhatsAppProviderConfigPayload,
    WhatsAppProviderConfigSummary,
    WhatsAppSendMessagePayload,
)
from bioma_api.services import whatsapp as whatsapp_service

router = APIRouter(prefix="/workspaces/{workspace_id}/whatsapp", tags=["whatsapp-multiprovider"])


@router.get("/providers", response_model=list[WhatsAppProviderConfigSummary])
def list_providers(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WhatsAppProviderConfigSummary]:
    return whatsapp_service.list_providers(workspace_id, user)


@router.post("/providers", response_model=WhatsAppProviderConfigSummary)
def upsert_provider(
    workspace_id: UUID,
    payload: WhatsAppProviderConfigPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WhatsAppProviderConfigSummary:
    return whatsapp_service.upsert_provider(workspace_id, payload, user)


@router.post("/send", response_model=WhatsAppMessageLogSummary, status_code=status.HTTP_201_CREATED)
def send_message(
    workspace_id: UUID,
    payload: WhatsAppSendMessagePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WhatsAppMessageLogSummary:
    return whatsapp_service.send_message(workspace_id, payload, user)


@router.get("/logs", response_model=list[WhatsAppMessageLogSummary])
def list_logs(
    workspace_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WhatsAppMessageLogSummary]:
    return whatsapp_service.list_logs(workspace_id, user, limit)
