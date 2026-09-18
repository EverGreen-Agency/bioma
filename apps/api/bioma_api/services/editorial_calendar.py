from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from psycopg.errors import UniqueViolation

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.db import connect
from bioma_api.repositories import editorial_calendar as cal_repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.editorial_calendar import (
    EditorialCalendarItemPayload,
    EditorialCalendarItemUpdate,
    EditorialCalendarItemSummary,
)


def list_items(
    workspace_id: UUID,
    user: CurrentUserResponse,
    stage: str | None = None,
    limit: int = 100,
) -> list[EditorialCalendarItemSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = cal_repo.list_calendar_items(conn, client["workspace_id"], stage, limit)
    return [EditorialCalendarItemSummary(**dict(r)) for r in rows]


def create_item(
    workspace_id: UUID,
    payload: EditorialCalendarItemPayload,
    user: CurrentUserResponse,
) -> EditorialCalendarItemSummary:
    try:
        with connect() as conn:
            client = _accessible_workspace(conn, workspace_id, user, "manage_work")
            if payload.stage != "ideation":
                raise HTTPException(status_code=422, detail="Novos itens começam em ideação.")
            data = _canonical_create_payload(conn, client["workspace_id"], payload.model_dump())
            row = cal_repo.create_calendar_item(conn, client["workspace_id"], data)
            _audit(conn, user, client, "calendar.created", row, None)
    except UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="Este rascunho já foi adicionado ao calendário.") from exc
    return EditorialCalendarItemSummary(**dict(row))


def _canonical_create_payload(conn, workspace_id: UUID, data: dict) -> dict:
    metadata = data.get("metadata") or {}
    if metadata.get("source_type") != "ai_content_request":
        return data
    try:
        request_id = UUID(str(metadata["ai_content_request_id"]))
        raw_index = metadata["output_index"]
        if isinstance(raw_index, bool) or not str(raw_index).isdigit():
            raise ValueError("Índice inválido")
        index = int(raw_index)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Origem de IA inválida.") from exc
    source = cal_repo.get_ready_ai_content_request(conn, workspace_id, request_id)
    posts = (source["output"] or {}).get("posts") if source else None
    if not isinstance(posts, list) or index >= len(posts):
        raise HTTPException(status_code=422, detail="Rascunho de IA indisponível neste workspace.")
    post = posts[index]
    data.update({
        "title": post["title"],
        "content_type": "social_post",
        "channel": post["channel"],
        "post_text": post["caption"],
        "scheduled_at": None,
        "media_urls": [],
        "metadata": {
            "source_type": "ai_content_request",
            "ai_content_request_id": str(request_id),
            "output_index": index,
            "generation_mode": source["generation_mode"],
            "provider": source["provider"],
            "model": source["model"],
        },
    })
    return data


def update_item(
    workspace_id: UUID,
    item_id: UUID,
    payload: EditorialCalendarItemUpdate,
    user: CurrentUserResponse,
) -> EditorialCalendarItemSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user, "manage_work")
        existing = cal_repo.get_calendar_item_for_update(conn, client["workspace_id"], item_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        if existing["stage"] in ("approved", "scheduled", "published"):
            raise HTTPException(status_code=409, detail="Volte o item para revisão antes de editar.")
        row = cal_repo.update_calendar_item(conn, client["workspace_id"], item_id, payload.model_dump())
        _audit(conn, user, client, "calendar.updated", row, existing["stage"])
    return EditorialCalendarItemSummary(**dict(row))


TRANSITIONS = {
    "ideation": {"production"},
    "production": {"review"},
    "review": {"production", "approved"},
    "approved": {"review", "scheduled"},
    "scheduled": {"approved"},
    "published": set(),
}


def update_stage(
    workspace_id: UUID,
    item_id: UUID,
    stage: str,
    user: CurrentUserResponse,
) -> EditorialCalendarItemSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        existing = cal_repo.get_calendar_item_for_update(conn, client["workspace_id"], item_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        capability = "approve" if existing["stage"] == "review" and stage == "approved" else "manage_work"
        require_workspace_capability(client, user, capability)
        if stage not in TRANSITIONS.get(existing["stage"], set()):
            raise HTTPException(status_code=409, detail="Transição de etapa inválida.")
        if stage in ("approved", "scheduled") and not (existing["post_text"] or "").strip():
            raise HTTPException(status_code=422, detail="A peça precisa de texto antes da aprovação.")
        if stage == "scheduled":
            scheduled_at = existing["scheduled_at"]
            if not scheduled_at or scheduled_at <= datetime.now(timezone.utc):
                raise HTTPException(status_code=422, detail="Escolha uma data e hora futuras antes de agendar.")
        row = cal_repo.update_calendar_stage(conn, client["workspace_id"], item_id, stage)
        _audit(conn, user, client, "calendar.stage_changed", row, existing["stage"])
    return EditorialCalendarItemSummary(**dict(row))


def _audit(conn, user, client, event_type, row, previous_stage):
    client_hub_repo.write_audit(conn, user.id, client["organization_id"], event_type, {
        "workspace_id": str(client["workspace_id"]),
        "item_id": str(row["id"]),
        "previous_stage": previous_stage,
        "stage": row["stage"],
    })


def _accessible_workspace(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "content")
    if capability:
        require_workspace_capability(client, user, capability)
    return client
