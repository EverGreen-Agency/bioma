from uuid import UUID

from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.local_radar import (
    LocalRadarImportRequest,
    LocalRadarProspect,
    LocalRadarScanCreate,
    LocalRadarScanDetail,
    LocalRadarScanSummary,
    ProspectDecisionPayload,
    ProspectMessagePayload,
    ProspectSendPayload,
    ProspectSendResult,
)
from bioma_api.services import local_radar as service

router = APIRouter(prefix="/backoffice/local-radar", tags=["local-radar"])


@router.post("/scans", response_model=LocalRadarScanDetail, status_code=status.HTTP_201_CREATED)
def create_scan(
    payload: LocalRadarScanCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> LocalRadarScanDetail:
    return service.create_scan(payload, user)


@router.post("/scans/import", response_model=LocalRadarScanDetail, status_code=status.HTTP_201_CREATED)
def import_scan(
    payload: LocalRadarImportRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> LocalRadarScanDetail:
    return service.import_scan(payload, user)


@router.get("/scans", response_model=list[LocalRadarScanSummary])
def list_scans(user: CurrentUserResponse = Depends(current_user_from_request)) -> list[LocalRadarScanSummary]:
    return service.list_scans(user)


@router.get("/scans/{scan_id}", response_model=LocalRadarScanDetail)
def get_scan(
    scan_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> LocalRadarScanDetail:
    return service.get_scan(scan_id, user)


@router.post("/prospects/{prospect_id}/audit", response_model=LocalRadarProspect)
def run_audit(
    prospect_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> LocalRadarProspect:
    return service.run_audit(prospect_id, user)


@router.patch("/prospects/{prospect_id}/message", response_model=LocalRadarProspect)
def update_message(
    prospect_id: UUID,
    payload: ProspectMessagePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> LocalRadarProspect:
    return service.update_message(prospect_id, payload, user)


@router.post("/prospects/{prospect_id}/decision", response_model=LocalRadarProspect)
def decide(
    prospect_id: UUID,
    payload: ProspectDecisionPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> LocalRadarProspect:
    return service.decide(prospect_id, payload, user)


@router.post("/prospects/{prospect_id}/send", response_model=ProspectSendResult)
def send_whatsapp(
    prospect_id: UUID,
    payload: ProspectSendPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ProspectSendResult:
    return service.send_whatsapp(prospect_id, payload, user)
