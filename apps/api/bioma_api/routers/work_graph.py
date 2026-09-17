from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.work_graph import (
    WorkGraphProjection,
    WorkItem,
    WorkItemCreate,
    WorkItemUpdate,
    WorkItemMaterializeRequest,
    WorkLink,
    WorkLinkCreate,
)
from bioma_api.services import work_graph as service


router = APIRouter(prefix="/workspaces/{workspace_id}/work-graph", tags=["work-graph"])


@router.get("", response_model=WorkGraphProjection)
def projection(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkGraphProjection:
    return service.projection(workspace_id, user)


@router.post("/items", response_model=WorkItem, status_code=status.HTTP_201_CREATED)
def create_item(
    workspace_id: UUID,
    payload: WorkItemCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkItem:
    return service.create_item(workspace_id, payload, user)


@router.patch("/items/{item_id}", response_model=WorkItem)
def update_item(
    workspace_id: UUID,
    item_id: UUID,
    payload: WorkItemUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkItem:
    return service.update_item(workspace_id, item_id, payload, user)


@router.post("/items/{item_id}/materialize-task", response_model=WorkItem)
def materialize_item(
    workspace_id: UUID,
    item_id: UUID,
    payload: WorkItemMaterializeRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkItem:
    return service.materialize_item(workspace_id, item_id, payload, user)


@router.post("/links", response_model=WorkLink, status_code=status.HTTP_201_CREATED)
def create_link(
    workspace_id: UUID,
    payload: WorkLinkCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WorkLink:
    return service.create_link(workspace_id, payload, user)


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(
    workspace_id: UUID,
    link_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> Response:
    service.delete_link(workspace_id, link_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
