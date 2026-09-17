from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.certifications import (
    CertificationCreateRequest,
    CertificationSummary,
    CertificationUpdateRequest,
)
from bioma_api.services import certifications as cert_service

router = APIRouter(prefix="/backoffice/certifications", tags=["certifications"])


@router.get("", response_model=list[CertificationSummary])
def list_certifications(
    user_id: UUID | None = Query(default=None),
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return cert_service.list_certifications(user, user_id)


@router.post("", response_model=CertificationSummary, status_code=201)
def create_certification(payload: CertificationCreateRequest, user: CurrentUserResponse = Depends(current_user_from_request)):
    return cert_service.create_certification(payload, user)


@router.patch("/{certification_id}", response_model=CertificationSummary)
def update_certification(
    certification_id: UUID,
    payload: CertificationUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return cert_service.update_certification(certification_id, payload, user)


@router.delete("/{certification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certification(certification_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    cert_service.delete_certification(certification_id, user)
