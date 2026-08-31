from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.market_research import (
    MarketResearchCreate,
    MarketResearchDetail,
    MarketResearchRefineRequest,
    MarketResearchRefinement,
    MarketResearchSummary,
)
from bioma_api.services import market_research as service


router = APIRouter(
    prefix="/workspaces/{workspace_id}/market-research",
    tags=["market-research"],
)


@router.get("", response_model=list[MarketResearchSummary])
def list_researches(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[MarketResearchSummary]:
    return service.list_researches(workspace_id, user)


@router.post("/refine", response_model=MarketResearchRefinement)
def refine_sector(
    workspace_id: UUID,
    payload: MarketResearchRefineRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> MarketResearchRefinement:
    return service.refine_sector(workspace_id, payload, user)


@router.post("", response_model=MarketResearchDetail, status_code=status.HTTP_201_CREATED)
def create_research(
    workspace_id: UUID,
    payload: MarketResearchCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> MarketResearchDetail:
    return service.create_research(workspace_id, payload, user)


@router.get("/{research_id}", response_model=MarketResearchDetail)
def get_research(
    workspace_id: UUID,
    research_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> MarketResearchDetail:
    research = service.get_research(research_id, user)
    if research.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesquisa não encontrada.")
    return research
