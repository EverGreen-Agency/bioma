from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.prospecting import (
    CreateProspectingListRequest,
    ProspectingCockpitContextResponse,
    ProspectingListDetailResponse,
    ProspectingListSummaryResponse,
    ProspectingSessionResponse,
    RecordDispositionRequest,
    SalesKnowledgeCardResponse,
    SalesKnowledgeCardStatusUpdate,
    StartProspectingSessionRequest,
)
from bioma_api.services import prospecting as prospecting_service

router = APIRouter(prefix="/workspaces/{workspace_id}/prospecting", tags=["prospecting"])


# ==========================================
# Sales Knowledge Cards Endpoints
# ==========================================

@router.get("/knowledge/cards", response_model=list[SalesKnowledgeCardResponse])
def list_knowledge_cards(
    workspace_id: UUID,
    query: str | None = Query(None, description="Busca textual por título, código ou roteiro"),
    motion: str | None = Query(None, description="Filtro por motion: growth, ai_automation ou all"),
    card_type: str | None = Query(None, description="Filtro por tipo: objection, battlecard, etc."),
    status: str | None = Query(None, description="Filtro por status: TESTING, VALIDATED, etc."),
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.list_knowledge_cards(
        workspace_id=workspace_id,
        user=user,
        query=query,
        motion=motion,
        card_type=card_type,
        status_filter=status,
    )


@router.patch("/knowledge/cards/{card_id}/status", response_model=SalesKnowledgeCardResponse)
def update_card_status(
    workspace_id: UUID,
    card_id: UUID,
    payload: SalesKnowledgeCardStatusUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.update_knowledge_card_status(
        workspace_id=workspace_id,
        card_id=card_id,
        payload=payload,
        user=user,
    )


# ==========================================
# Prospecting Lists Endpoints
# ==========================================

@router.get("/lists", response_model=list[ProspectingListSummaryResponse])
def list_prospecting_lists(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.list_prospecting_lists(workspace_id=workspace_id, user=user)


@router.post("/lists", response_model=ProspectingListSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_prospecting_list(
    workspace_id: UUID,
    payload: CreateProspectingListRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.create_prospecting_list(
        workspace_id=workspace_id,
        payload=payload,
        user=user,
    )


@router.get("/lists/{list_id}", response_model=ProspectingListDetailResponse)
def get_prospecting_list(
    workspace_id: UUID,
    list_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.get_prospecting_list(
        workspace_id=workspace_id,
        list_id=list_id,
        user=user,
    )


# ==========================================
# Prospecting Sessions (Focus Mode) Endpoints
# ==========================================

@router.post("/sessions", response_model=ProspectingSessionResponse, status_code=status.HTTP_201_CREATED)
def start_prospecting_session(
    workspace_id: UUID,
    payload: StartProspectingSessionRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.start_prospecting_session(
        workspace_id=workspace_id,
        payload=payload,
        user=user,
    )


@router.get("/sessions/{session_id}/cockpit", response_model=ProspectingCockpitContextResponse)
def get_session_cockpit(
    workspace_id: UUID,
    session_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.get_session_cockpit(
        workspace_id=workspace_id,
        session_id=session_id,
        user=user,
    )


@router.post("/sessions/{session_id}/disposition", response_model=ProspectingCockpitContextResponse)
def record_session_disposition(
    workspace_id: UUID,
    session_id: UUID,
    payload: RecordDispositionRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.record_session_disposition(
        workspace_id=workspace_id,
        session_id=session_id,
        payload=payload,
        user=user,
    )


@router.post("/sessions/{session_id}/finish", response_model=ProspectingSessionResponse)
def finish_session(
    workspace_id: UUID,
    session_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return prospecting_service.finish_session(
        workspace_id=workspace_id,
        session_id=session_id,
        user=user,
    )
