from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.client_profile import ClientProfilePayload, ClientProfileSummary
from bioma_api.services import client_profiles as profile_service


router = APIRouter(prefix="/workspaces/{workspace_id}/client-profile", tags=["client-profile"])


@router.get("", response_model=ClientProfileSummary)
def get_client_profile(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientProfileSummary:
    return profile_service.get_profile(workspace_id, user)


@router.patch("", response_model=ClientProfileSummary)
def upsert_client_profile(
    workspace_id: UUID,
    payload: ClientProfilePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientProfileSummary:
    return profile_service.upsert_profile(workspace_id, payload, user)
