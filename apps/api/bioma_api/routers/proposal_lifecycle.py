from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.proposal_lifecycle import (
    ProposalAcceptanceCreate,
    ProposalArchiveRequest,
    ProposalClaimsReview,
    ProposalCohortAnalytics,
    ProposalContentUpdate,
    ProposalConversionCreate,
    ProposalDeliveryCreate,
    ProposalDetailResponse,
    ProposalLifecycleRecord,
    PublicProposalLifecycleRecord,
    ProposalRevisionCreate,
    ProposalStatusTransition,
)
from bioma_api.services import proposal_lifecycle as lifecycle_service


router = APIRouter(prefix="/backoffice/proposals", tags=["proposal-lifecycle"])
public_router = APIRouter(prefix="/proposals", tags=["public-proposal-lifecycle"])


@router.get("/cohorts", response_model=ProposalCohortAnalytics)
def get_cohorts(user: CurrentUserResponse = Depends(current_user_from_request)):
    return lifecycle_service.cohort_analytics(user)


@router.get("/{proposal_id}", response_model=ProposalDetailResponse)
def get_proposal_detail(
    proposal_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return lifecycle_service.get_detail(proposal_id, user)


@router.put("/{proposal_id}/content", response_model=ProposalDetailResponse)
def update_proposal_content(
    proposal_id: UUID,
    payload: ProposalContentUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return lifecycle_service.update_content(proposal_id, payload, user)


@router.post("/{proposal_id}/claims-review", response_model=ProposalDetailResponse)
def review_proposal_claims(
    proposal_id: UUID,
    payload: ProposalClaimsReview,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return lifecycle_service.review_claims(proposal_id, payload, user)


@router.post("/{proposal_id}/transition", response_model=ProposalDetailResponse)
def transition_proposal(
    proposal_id: UUID,
    payload: ProposalStatusTransition,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return lifecycle_service.transition_status(proposal_id, payload, user)


@router.post(
    "/{proposal_id}/revisions",
    response_model=ProposalDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_proposal_revision(
    proposal_id: UUID,
    payload: ProposalRevisionCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return lifecycle_service.create_revision(proposal_id, payload, user)


@router.post(
    "/{proposal_id}/deliveries",
    response_model=ProposalDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_proposal_delivery(
    proposal_id: UUID,
    payload: ProposalDeliveryCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return lifecycle_service.create_delivery(proposal_id, payload, user)


@router.post("/{proposal_id}/convert", response_model=ProposalDetailResponse)
def convert_proposal(
    proposal_id: UUID,
    payload: ProposalConversionCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return lifecycle_service.convert_to_project(proposal_id, payload, user)


@router.get("/{proposal_id}/pdf")
def export_proposal_pdf(
    proposal_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    content, filename = lifecycle_service.pdf_bytes(proposal_id, user)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_proposal(
    proposal_id: UUID,
    payload: ProposalArchiveRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    lifecycle_service.archive(proposal_id, payload, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.get("/public/{public_token}/detail", response_model=PublicProposalLifecycleRecord)
def get_public_proposal_detail(public_token: str):
    return lifecycle_service.get_public_detail(public_token)


@public_router.post("/public/{public_token}/accept", response_model=PublicProposalLifecycleRecord)
def accept_public_proposal(public_token: str, payload: ProposalAcceptanceCreate):
    return lifecycle_service.accept_public(public_token, payload)
