from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.offer_lab import (
    OfferEvaluatePayload,
    OfferValidationResponse,
)
from bioma_api.services import offer_lab as offer_lab_service

router = APIRouter(prefix="/offer-lab", tags=["offer-lab"])
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}/offer-validations", tags=["workspace-offer-validations"])
client_router = APIRouter(prefix="/clients/{client_id}/offer-validations", tags=["client-offer-validations"])


@router.post("/evaluate")
def evaluate_offer_preview(
    payload: OfferEvaluatePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict:
    """Simulação e avaliação de oferta em tempo real pelo conselho consultivo."""
    return offer_lab_service.evaluate_offer_preview(payload)


@workspace_router.get("", response_model=list[OfferValidationResponse])
@client_router.get("", response_model=list[OfferValidationResponse])
def list_validations(
    workspace_id: UUID | None = None,
    client_id: UUID | None = None,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[OfferValidationResponse]:
    target_id = workspace_id or client_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Identificador de workspace ou cliente obrigatório.")
    return offer_lab_service.list_workspace_validations(target_id, user)


@workspace_router.post("", response_model=OfferValidationResponse, status_code=status.HTTP_201_CREATED)
@client_router.post("", response_model=OfferValidationResponse, status_code=status.HTTP_201_CREATED)
def create_validation(
    payload: OfferEvaluatePayload,
    workspace_id: UUID | None = None,
    client_id: UUID | None = None,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> OfferValidationResponse:
    target_id = workspace_id or client_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Identificador de workspace ou cliente obrigatório.")
    return offer_lab_service.create_workspace_validation(target_id, payload, user)


@workspace_router.get("/{validation_id}", response_model=OfferValidationResponse)
@client_router.get("/{validation_id}", response_model=OfferValidationResponse)
def get_validation(
    validation_id: UUID,
    workspace_id: UUID | None = None,
    client_id: UUID | None = None,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> OfferValidationResponse:
    target_id = workspace_id or client_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Identificador de workspace ou cliente obrigatório.")
    return offer_lab_service.get_workspace_validation(target_id, validation_id, user)


@workspace_router.delete("/{validation_id}", status_code=status.HTTP_204_NO_CONTENT)
@client_router.delete("/{validation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_validation(
    validation_id: UUID,
    workspace_id: UUID | None = None,
    client_id: UUID | None = None,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    target_id = workspace_id or client_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Identificador de workspace ou cliente obrigatório.")
    offer_lab_service.delete_workspace_validation(target_id, validation_id, user)
