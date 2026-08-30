from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.proposals import (
    OpportunityCreatePayload,
    CommercialActivityCreate,
    OpportunityContactCreate,
    OpportunityDetail,
    OpportunityIngestPayload,
    OpportunityPlatformSummary,
    OpportunityPlatformUpdate,
    OpportunitySummary,
    OpportunityUpdatePayload,
    FreelancerProfileSyncRequest,
    ProposalBriefCreatePayload,
    ProposalCreatePayload,
    ProposalSummary,
    ProposalTranslateRequest,
    ProposalTranslation,
    ProposalUpdatePayload,
    PublicProposalResponse,
)
from bioma_api.services import proposals as proposals_service

router = APIRouter(prefix="/backoffice/proposals", tags=["proposals"])
public_router = APIRouter(prefix="/proposals", tags=["public-proposals"])


@router.get("/catalog")
def get_proposal_catalog(
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.get_proposal_catalog(user)


@router.get("/opportunities", response_model=list[OpportunitySummary])
def list_opportunities(
    status: str | None = Query(None),
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.list_opportunities(user, status_filter=status)


@router.post("/opportunities/ingest", response_model=OpportunitySummary, status_code=status.HTTP_201_CREATED)
def ingest_opportunity(
    payload: OpportunityIngestPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.ingest_opportunity(payload, user)


@router.get("/opportunities/{opp_id}", response_model=OpportunityDetail)
def get_opportunity(
    opp_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.get_opportunity_detail(opp_id, user)


@router.patch("/opportunities/{opp_id}", response_model=OpportunityDetail)
def update_opportunity(
    opp_id: UUID,
    payload: OpportunityUpdatePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.update_opportunity(opp_id, payload, user)


@router.post("/opportunities/{opp_id}/activities", response_model=OpportunityDetail, status_code=status.HTTP_201_CREATED)
def add_opportunity_activity(
    opp_id: UUID,
    payload: CommercialActivityCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.add_commercial_activity(opp_id, payload, user)


@router.post("/opportunities/{opp_id}/contacts", response_model=OpportunityDetail, status_code=status.HTTP_201_CREATED)
def add_opportunity_contact(
    opp_id: UUID,
    payload: OpportunityContactCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.add_opportunity_contact(opp_id, payload, user)


@router.post("/opportunities/sync")
def sync_opportunities(
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.sync_opportunities_from_scrapers(user)


@router.post("/opportunities/{opp_id}/evaluate-ai", response_model=OpportunitySummary)
def evaluate_opportunity_ai(
    opp_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.evaluate_opportunity_with_ai(opp_id, user)


@router.get("/platforms", response_model=list[OpportunityPlatformSummary])
def list_platforms(
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.list_platform_configs(user)


@router.put("/platforms/{platform_key}", response_model=OpportunityPlatformSummary)
def update_platform(
    platform_key: str,
    payload: OpportunityPlatformUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.update_platform_config(platform_key, payload, user)


@router.get("/profiles")
def list_freelancer_profiles(
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.list_freelancer_profiles(user)


@router.post("/profiles/sync")
def sync_freelancer_profile(
    payload: FreelancerProfileSyncRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.sync_and_audit_freelancer_profile(
        str(payload.profile_url),
        payload.platform_key,
        user,
    )


@router.delete("/profiles/{profile_id}")
def delete_freelancer_profile(
    profile_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.delete_freelancer_profile(profile_id, user)


@router.get("/skills")
def list_skills(
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.list_tech_skills(user)


@router.get("/gaps")
def list_gaps(
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.list_skill_gaps(user)


@router.post("/gaps/{gap_id}/resolve")
def resolve_gap(
    gap_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.resolve_skill_gap(gap_id, user)


@router.get("/analytics")
def get_analytics(
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.get_proposal_analytics(user)







@router.post("/opportunities/{opp_id}/generate", response_model=ProposalSummary, status_code=status.HTTP_201_CREATED)
def generate_proposal(
    opp_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.generate_proposal_for_opportunity(opp_id, user)


@router.get("", response_model=list[ProposalSummary])
def list_proposals(
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.list_proposals(user)


@router.post("", response_model=ProposalSummary, status_code=status.HTTP_201_CREATED)
def create_proposal(
    payload: ProposalCreatePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.create_proposal(payload, user)


@router.post("/from-brief", response_model=ProposalSummary, status_code=status.HTTP_201_CREATED)
def create_proposal_from_brief(
    payload: ProposalBriefCreatePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.generate_proposal_from_brief(payload, user)


@router.patch("/{proposal_id}", response_model=ProposalSummary)
def update_proposal(
    proposal_id: UUID,
    payload: ProposalUpdatePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return proposals_service.update_proposal(proposal_id, payload, user)


@router.post("/{proposal_id}/translate", response_model=ProposalTranslation)
def translate_proposal(
    proposal_id: UUID,
    payload: ProposalTranslateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    """Uso interno da EG — o link público nunca muda de idioma. Primeira
    chamada naquele idioma traduz e guarda; as seguintes leem do cache."""
    return proposals_service.translate_proposal(proposal_id, payload, user)


@public_router.get("/public/{public_token}", response_model=PublicProposalResponse)
def get_public_proposal(public_token: str):
    return proposals_service.get_public_proposal(public_token)
