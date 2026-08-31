from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.briefing import BriefingDraftResponse
from bioma_api.services import briefing as service

router = APIRouter(prefix="/workspaces/{workspace_id}/briefing", tags=["briefing"])


@router.post("/draft", response_model=BriefingDraftResponse)
def build_draft(
    workspace_id: UUID,
    persist: bool = False,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> BriefingDraftResponse:
    """Monta o rascunho a partir dos sinais reais do cliente.

    `persist=false` (padrão) só devolve para revisão na tela; `persist=true`
    grava como artefato `briefing` interno.
    """
    return service.build_draft(workspace_id, user, persist)
