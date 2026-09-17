from uuid import UUID
from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module
from bioma_api.db import connect
from bioma_api.repositories import brand_book as brand_repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.brand_book import BrandBookPayload, BrandBookSummary


def get_brand_book(workspace_id: UUID, user: CurrentUserResponse) -> BrandBookSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        row = brand_repo.get_active_brand_book(conn, client["workspace_id"])
    return BrandBookSummary(**dict(row))


def upsert_brand_book(
    workspace_id: UUID,
    payload: BrandBookPayload,
    user: CurrentUserResponse,
) -> BrandBookSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        row = brand_repo.upsert_brand_book(conn, client["workspace_id"], payload.model_dump())
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "brand_book.updated",
            {"workspace_id": str(client["workspace_id"]), "version": row["version"]},
        )
    return BrandBookSummary(**dict(row))


def _accessible_workspace(conn, workspace_id: UUID, user: CurrentUserResponse):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "content")
    return client
