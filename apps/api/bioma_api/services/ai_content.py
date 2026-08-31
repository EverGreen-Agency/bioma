from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.db import connect
from bioma_api.repositories import ai_content as ai_content_repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.ai_content import AiContentRequestCreate, AiContentRequestSummary
from bioma_api.schemas.auth import CurrentUserResponse


def list_requests(workspace_id: UUID, user: CurrentUserResponse) -> list[AiContentRequestSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = ai_content_repo.list_requests(conn, client["workspace_id"])
    return [AiContentRequestSummary(**row) for row in rows]


def create_request(
    workspace_id: UUID,
    payload: AiContentRequestCreate,
    user: CurrentUserResponse,
) -> AiContentRequestSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user, "generate_content")
        row = ai_content_repo.create_request(
            conn,
            client["workspace_id"],
            client["organization_id"],
            user.id,
            payload.model_dump(),
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "ai.content_requested",
            {
                "workspace_id": str(client["workspace_id"]),
                "request_id": str(row["id"]),
                "quantity": payload.quantity,
                "channels": payload.channels,
            },
        )
    return AiContentRequestSummary(**row)


def _accessible_workspace(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "content")
    if capability:
        require_workspace_capability(client, user, capability)
    return client
