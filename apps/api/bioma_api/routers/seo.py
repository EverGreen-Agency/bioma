from uuid import UUID

from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.seo import SeoCollectRequest, SeoSnapshotState
from bioma_api.services import seo as service


router = APIRouter(prefix="/workspaces", tags=["seo"])


@router.get("/{workspace_id}/seo", response_model=SeoSnapshotState)
def get_seo_snapshot(workspace_id: UUID, user: CurrentUserResponse = Depends(current_user_from_request)):
    return service.get_snapshot_state(workspace_id, user)


@router.post("/{workspace_id}/seo/snapshots", response_model=SeoSnapshotState, status_code=status.HTTP_201_CREATED)
def collect_seo_snapshot(
    workspace_id: UUID,
    payload: SeoCollectRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return service.collect_snapshot(workspace_id, payload.target, user)
