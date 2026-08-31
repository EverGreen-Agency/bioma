from uuid import UUID

from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.vault import (
    VaultCopyRequest,
    VaultCopyResponse,
    VaultCredentialCreate,
    VaultCredentialSummary,
    VaultCredentialUpdate,
    VaultReasonRequest,
    VaultRevealResponse,
    VaultStatusUpdate,
)
from bioma_api.services import vault as vault_service


router = APIRouter(prefix="/workspaces/{workspace_id}/vault", tags=["access-vault"])


@router.get("", response_model=list[VaultCredentialSummary])
def list_credentials(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[VaultCredentialSummary]:
    return vault_service.list_credentials(workspace_id, user)


@router.post("", response_model=VaultCredentialSummary, status_code=status.HTTP_201_CREATED)
def create_credential(
    workspace_id: UUID,
    payload: VaultCredentialCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> VaultCredentialSummary:
    return vault_service.create_credential(workspace_id, payload, user)


@router.patch("/{credential_id}", response_model=VaultCredentialSummary)
def update_credential(
    workspace_id: UUID,
    credential_id: UUID,
    payload: VaultCredentialUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> VaultCredentialSummary:
    return vault_service.update_credential(workspace_id, credential_id, payload, user)


@router.patch("/{credential_id}/status", response_model=VaultCredentialSummary)
def set_status(
    workspace_id: UUID,
    credential_id: UUID,
    payload: VaultStatusUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> VaultCredentialSummary:
    return vault_service.set_status(workspace_id, credential_id, payload, user)


@router.post("/{credential_id}/reveal", response_model=VaultRevealResponse)
def reveal_credential(
    workspace_id: UUID,
    credential_id: UUID,
    payload: VaultReasonRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> VaultRevealResponse:
    return vault_service.reveal_credential(workspace_id, credential_id, payload, user)


@router.post("/{credential_id}/copy", response_model=VaultCopyResponse)
def copy_secret(
    workspace_id: UUID,
    credential_id: UUID,
    payload: VaultCopyRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> VaultCopyResponse:
    return vault_service.copy_secret(workspace_id, credential_id, payload, user)
