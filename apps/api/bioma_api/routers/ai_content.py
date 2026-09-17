from uuid import UUID

from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.ai_content import AiContentRequestCreate, AiContentRequestSummary
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services import ai_content as ai_content_service


router = APIRouter(prefix="/workspaces/{workspace_id}/ai/content", tags=["ai-content"])


@router.get("", response_model=list[AiContentRequestSummary])
def list_requests(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[AiContentRequestSummary]:
    return ai_content_service.list_requests(workspace_id, user)


@router.post("", response_model=AiContentRequestSummary, status_code=status.HTTP_202_ACCEPTED)
def create_request(
    workspace_id: UUID,
    payload: AiContentRequestCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiContentRequestSummary:
    return ai_content_service.create_request(workspace_id, payload, user)
