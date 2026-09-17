from uuid import UUID

from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.kits import (
    KitDefinitionCreateRequest,
    KitDefinitionSummary,
    KitDefinitionUpdateRequest,
    KitPieceCreateRequest,
    KitPieceSummary,
    KitPieceUpdateRequest,
    KitShipmentCreateRequest,
    KitShipmentStatusUpdateRequest,
    KitShipmentSummary,
)
from bioma_api.services import kits as kits_service

router = APIRouter(prefix="/backoffice/logistics", tags=["logistics"])


@router.get("/pieces", response_model=list[KitPieceSummary])
def list_pieces(user: CurrentUserResponse = Depends(current_user_from_request)):
    return kits_service.list_pieces(user)


@router.post("/pieces", response_model=KitPieceSummary, status_code=201)
def create_piece(payload: KitPieceCreateRequest, user: CurrentUserResponse = Depends(current_user_from_request)):
    return kits_service.create_piece(payload, user)


@router.patch("/pieces/{piece_id}", response_model=KitPieceSummary)
def update_piece(piece_id: UUID, payload: KitPieceUpdateRequest, user: CurrentUserResponse = Depends(current_user_from_request)):
    return kits_service.update_piece(piece_id, payload, user)


@router.get("/kits", response_model=list[KitDefinitionSummary])
def list_kit_definitions(user: CurrentUserResponse = Depends(current_user_from_request)):
    return kits_service.list_kit_definitions(user)


@router.post("/kits", response_model=KitDefinitionSummary, status_code=201)
def create_kit_definition(payload: KitDefinitionCreateRequest, user: CurrentUserResponse = Depends(current_user_from_request)):
    return kits_service.create_kit_definition(payload, user)


@router.patch("/kits/{kit_definition_id}", response_model=KitDefinitionSummary)
def update_kit_definition(
    kit_definition_id: UUID,
    payload: KitDefinitionUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return kits_service.update_kit_definition(kit_definition_id, payload, user)


@router.get("/shipments", response_model=list[KitShipmentSummary])
def list_shipments(
    client_id: UUID | None = Query(default=None),
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return kits_service.list_shipments(user, client_id)


@router.post("/shipments", response_model=KitShipmentSummary, status_code=201)
def create_shipment(payload: KitShipmentCreateRequest, user: CurrentUserResponse = Depends(current_user_from_request)):
    return kits_service.create_shipment(payload, user)


@router.patch("/shipments/{shipment_id}/status", response_model=KitShipmentSummary)
def update_shipment_status(
    shipment_id: UUID,
    payload: KitShipmentStatusUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return kits_service.update_shipment_status(shipment_id, payload, user)
