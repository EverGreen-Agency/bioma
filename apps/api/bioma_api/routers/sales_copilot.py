from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.sales_copilot import (
    FathomImportRequest,
    FathomImportResult,
    FathomMeeting,
    RealtimeAdapterStatus,
    SalesCopilotActionCreate,
    SalesCopilotActionMaterialize,
    SalesCopilotCompleteRequest,
    SalesCopilotEventCreate,
    SalesCopilotIngestionAck,
    SalesCopilotIngestionCredential,
    SalesCopilotLiveAnalyzeRequest,
    SalesCopilotMeetingConfigure,
    SalesCopilotMetrics,
    SalesCopilotParticipantCreate,
    SalesCopilotSession,
    SalesCopilotSessionCreate,
    SalesCopilotTranscriptBatch,
)
from bioma_api.services import sales_copilot as copilot_service


router = APIRouter(prefix="/backoffice/sales-copilot", tags=["sales-copilot"])


@router.get("", response_model=list[SalesCopilotSession])
def list_sessions(user: CurrentUserResponse = Depends(current_user_from_request)):
    return copilot_service.list_sessions(user)


@router.post("", response_model=SalesCopilotSession, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SalesCopilotSessionCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.create_session(payload, user)


@router.get("/metrics", response_model=SalesCopilotMetrics)
def get_metrics(user: CurrentUserResponse = Depends(current_user_from_request)):
    return copilot_service.metrics(user)


@router.get("/realtime-adapter", response_model=RealtimeAdapterStatus)
def get_realtime_adapter(user: CurrentUserResponse = Depends(current_user_from_request)):
    return copilot_service.realtime_adapter_status(user)


@router.post(
    "/ingest/{session_id}",
    response_model=SalesCopilotIngestionAck,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_external_transcript(
    session_id: UUID,
    payload: SalesCopilotTranscriptBatch,
    x_copilot_ingest_token: str = Header(),
):
    return copilot_service.ingest_external_transcript(
        session_id, payload, x_copilot_ingest_token,
    )


@router.get("/{session_id}", response_model=SalesCopilotSession)
def get_session(
    session_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.get_session(session_id, user)


@router.post("/{session_id}/prepare", response_model=SalesCopilotSession)
def prepare_session(
    session_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.prepare_session(session_id, user)


@router.put("/{session_id}/meeting", response_model=SalesCopilotSession)
def configure_meeting(
    session_id: UUID,
    payload: SalesCopilotMeetingConfigure,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.configure_meeting(session_id, payload, user)


@router.post(
    "/{session_id}/ingestion-credential",
    response_model=SalesCopilotIngestionCredential,
)
def issue_ingestion_credential(
    session_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.issue_ingestion_credential(session_id, user)


@router.post("/{session_id}/participants", response_model=SalesCopilotSession)
def add_participant(
    session_id: UUID,
    payload: SalesCopilotParticipantCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.add_participant(session_id, payload, user)


@router.post("/{session_id}/transcript-segments", response_model=SalesCopilotSession)
def ingest_transcript(
    session_id: UUID,
    payload: SalesCopilotTranscriptBatch,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.ingest_transcript(session_id, payload, user)


@router.post("/{session_id}/analyze-live", response_model=SalesCopilotSession)
def analyze_live(
    session_id: UUID,
    payload: SalesCopilotLiveAnalyzeRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.analyze_live(session_id, payload, user)


@router.post("/{session_id}/actions", response_model=SalesCopilotSession)
def add_action(
    session_id: UUID,
    payload: SalesCopilotActionCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.add_action(session_id, payload, user)


@router.post("/actions/{action_id}/materialize", response_model=SalesCopilotSession)
def materialize_action(
    action_id: UUID,
    payload: SalesCopilotActionMaterialize,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.materialize_action(action_id, payload, user)


@router.post("/{session_id}/events", response_model=SalesCopilotSession)
def add_event(
    session_id: UUID,
    payload: SalesCopilotEventCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.add_event(session_id, payload, user)


@router.post("/{session_id}/complete", response_model=SalesCopilotSession)
def complete_session(
    session_id: UUID,
    payload: SalesCopilotCompleteRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.complete_session(session_id, payload, user)


@router.post("/{session_id}/journey/rebuild", response_model=SalesCopilotSession)
def rebuild_journey(
    session_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return copilot_service.rebuild_journey(session_id, user)


@router.get("/fathom/meetings", response_model=list[FathomMeeting])
def list_fathom_meetings(
    limit: int = 20,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[FathomMeeting]:
    """Reuniões gravadas no Fathom disponíveis para importação."""
    return copilot_service.list_fathom_meetings(user, limit)


@router.post("/{session_id}/fathom-import", response_model=FathomImportResult)
def import_fathom_meeting(
    session_id: UUID,
    payload: FathomImportRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> FathomImportResult:
    """Importa a transcrição real da gravação para a sessão (idempotente)."""
    return copilot_service.import_fathom_meeting(session_id, payload, user)
