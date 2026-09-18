import hashlib
import json
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import seo as repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.seo import SeoSnapshotState, SeoSnapshotSummary
from bioma_api.worker_bridge import collect_dataforseo_domain_rank_safe


def _require_access(conn, workspace_id: UUID, user: CurrentUserResponse):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado ou sem acesso.")
    require_client_module(client, user, "commercial")
    return client


def get_snapshot_state(workspace_id: UUID, user: CurrentUserResponse) -> SeoSnapshotState:
    with connect() as conn:
        _require_access(conn, workspace_id, user)
        row = repo.latest_snapshot(conn, workspace_id)
    return SeoSnapshotState(available=row is not None, latest=SeoSnapshotSummary(**row) if row else None)


def collect_snapshot(workspace_id: UUID, target: str, user: CurrentUserResponse) -> SeoSnapshotState:
    require_platform_admin(user)
    with connect() as conn:
        client = _require_access(conn, workspace_id, user)
        organization_id = client["organization_id"]
    try:
        snapshot = collect_dataforseo_domain_rank_safe(target)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    raw_canonical = json.dumps(snapshot["raw_response"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(raw_canonical.encode("utf-8")).hexdigest()
    with connect() as conn:
        row = repo.insert_snapshot(conn, workspace_id, user.id, snapshot, digest)
        if row:
            client_hub_repo.write_audit(conn, user.id, organization_id, "seo.snapshot.collected", {
                "snapshot_id": str(row["id"]), "source": "dataforseo", "target": target,
                "has_data": snapshot["has_data"], "source_task_id": snapshot.get("source_task_id"),
            })
        else:
            row = repo.snapshot_by_hash(conn, workspace_id, digest)
    return SeoSnapshotState(available=True, latest=SeoSnapshotSummary(**row))
