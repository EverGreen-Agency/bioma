from uuid import UUID
from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.brand_book import BrandBookPayload, BrandBookSummary
from bioma_api.services import brand_book as brand_service

router = APIRouter(prefix="/workspaces/{workspace_id}/brand-book", tags=["brand-book"])


@router.get("", response_model=BrandBookSummary)
def get_brand_book(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> BrandBookSummary:
    return brand_service.get_brand_book(workspace_id, user)


@router.post("", response_model=BrandBookSummary, status_code=status.HTTP_201_CREATED)
def upsert_brand_book(
    workspace_id: UUID,
    payload: BrandBookPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> BrandBookSummary:
    return brand_service.upsert_brand_book(workspace_id, payload, user)
