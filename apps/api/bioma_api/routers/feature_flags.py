from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.feature_flags import FeatureFlag, FeatureFlagUpsert
from bioma_api.services import feature_flags as service

router = APIRouter(prefix="/organizations/{organization_id}/feature-flags", tags=["feature-flags"])


@router.get("", response_model=list[FeatureFlag])
def list_flags(
    organization_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[FeatureFlag]:
    """Estado efetivo de cada feature — inclui o que está 'em breve'."""
    return service.list_flags(organization_id, user)


@router.put("", response_model=list[FeatureFlag])
def upsert_flag(
    organization_id: UUID,
    payload: FeatureFlagUpsert,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[FeatureFlag]:
    return service.upsert_flag(organization_id, payload, user)


@router.delete("/{feature_key}", response_model=list[FeatureFlag])
def clear_flag(
    organization_id: UUID,
    feature_key: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[FeatureFlag]:
    """Remove a exceção e volta ao default do catálogo."""
    return service.clear_flag(organization_id, feature_key, user)
