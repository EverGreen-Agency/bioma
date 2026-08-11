from uuid import UUID

from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.ai_routing import (
    AiRoutingControlPlane,
    ModelCatalogUpsert,
    ProviderAccountCreate,
    ProviderAccountUpdate,
    QuotaBucketCreate,
    RoutePreview,
    RoutePreviewRequest,
    RoutingPolicyUpsert,
    WebSessionConnectPayload,
)
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services import ai_routing as service


router = APIRouter(prefix="/backoffice/ai-operations", tags=["ai-routing"])


@router.get("/control-plane", response_model=AiRoutingControlPlane)
def get_control_plane(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.get_control_plane(user)


@router.post("/accounts", response_model=AiRoutingControlPlane, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: ProviderAccountCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.create_account(payload, user)


@router.patch("/accounts/{account_id}", response_model=AiRoutingControlPlane)
def update_account(
    account_id: UUID,
    payload: ProviderAccountUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.update_account(account_id, payload, user)


@router.put("/accounts/{account_id}/models", response_model=AiRoutingControlPlane)
def upsert_model(
    account_id: UUID,
    payload: ModelCatalogUpsert,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.upsert_model(account_id, payload, user)


@router.post("/accounts/{account_id}/models/bootstrap", response_model=AiRoutingControlPlane)
def bootstrap_models(
    account_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.bootstrap_models(account_id, user)


@router.post("/accounts/{account_id}/connect-web-session", response_model=AiRoutingControlPlane)
def connect_web_session(
    account_id: UUID,
    payload: WebSessionConnectPayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.connect_web_session(account_id, payload, user)


@router.post(
    "/accounts/{account_id}/quota-buckets",
    response_model=AiRoutingControlPlane,
    status_code=status.HTTP_201_CREATED,
)
def record_quota(
    account_id: UUID,
    payload: QuotaBucketCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.record_quota(account_id, payload, user)


@router.post("/accounts/{account_id}/quota-collection", response_model=AiRoutingControlPlane, status_code=202)
def collect_quota(
    account_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.enqueue_quota_collection(account_id, user)


@router.put("/routing-policies", response_model=AiRoutingControlPlane)
def upsert_policy(
    payload: RoutingPolicyUpsert,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.upsert_policy(payload, user)


@router.post("/routing-policies/bootstrap", response_model=AiRoutingControlPlane)
def bootstrap_policies(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AiRoutingControlPlane:
    return service.bootstrap_policies(user)


@router.post("/route-preview", response_model=RoutePreview)
def preview_route(
    payload: RoutePreviewRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> RoutePreview:
    return service.preview_route(payload, user)
