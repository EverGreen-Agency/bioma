from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import resolve_accessible_client
from bioma_api.db import connect
from bioma_api.repositories import work_graph as repo
from bioma_api.repositories import tasks as tasks_repo
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


def _require_workspace(conn, workspace_id: UUID, user: CurrentUserResponse) -> None:
    # O grafo é operacional interno: manager/operator podem trabalhar nele;
    # client_user continua sem `manage_work` e não recebe a projeção.
    resolve_accessible_client(conn, workspace_id, user, capability="manage_work")


def projection(workspace_id: UUID, user: CurrentUserResponse) -> WorkGraphProjection:
    with connect() as conn:
        _require_workspace(conn, workspace_id, user)
        items = repo.list_items(conn, workspace_id)
        links = repo.list_links(conn, workspace_id)
    return WorkGraphProjection(
        items=[WorkItem(**row) for row in items],
        links=[WorkLink(**row) for row in links],
    )


def create_item(workspace_id: UUID, payload: WorkItemCreate, user: CurrentUserResponse) -> WorkItem:
    data = payload.model_dump()
    data["title"] = data["title"].strip()
    with connect() as conn:
        _require_workspace(conn, workspace_id, user)
        if payload.project_id and not repo.entity_exists(conn, workspace_id, "project", payload.project_id):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Projeto não pertence ao workspace.")
        if payload.source_document_import_id and not repo.entity_exists(
            conn, workspace_id, "document_import", payload.source_document_import_id
        ):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Importação não pertence ao workspace.")
        _validate_dates(data)
        row = repo.create_item(conn, workspace_id, data, user.id)
    return WorkItem(**row)


def update_item(
    workspace_id: UUID, item_id: UUID, payload: WorkItemUpdate, user: CurrentUserResponse
) -> WorkItem:
    fields = payload.model_dump(exclude_unset=True)
    if "title" in fields:
        fields["title"] = fields["title"].strip()
    with connect() as conn:
        _require_workspace(conn, workspace_id, user)
        current = repo.get_item(conn, item_id, workspace_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de trabalho não encontrado.")
        _validate_dates({**current, **fields})
        row = repo.update_item(conn, item_id, workspace_id, fields)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de trabalho não encontrado.")
    return WorkItem(**row)


def materialize_item(
    workspace_id: UUID,
    item_id: UUID,
    payload: WorkItemMaterializeRequest,
    user: CurrentUserResponse,
) -> WorkItem:
    with connect() as conn:
        _require_workspace(conn, workspace_id, user)
        item = repo.get_item(conn, item_id, workspace_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de trabalho não encontrado.")
        if item["materialized_task_id"]:
            return WorkItem(**item)
        priority = {"critical": "Alta", "high": "Alta", "medium": "Média", "low": "Baixa"}[item["priority"]]
        start_date = _as_midnight(item["planned_start_at"])
        due_date = _as_midnight(item["planned_end_at"])
        task = tasks_repo.create_task_in_workspace(
            conn,
            workspace_id,
            {
                "title": item["title"],
                "description": item["summary"],
                "acceptance_criteria": item["acceptance_criteria"],
                "definition_of_done": item["definition_of_done"],
                "status": "A fazer",
                "group_status": "NOT_STARTED",
                "priority": priority,
                "start_date": start_date,
                "due_date": due_date,
                "recurrence": "none",
                "client_visible": False,
                "project_id": item["project_id"],
            },
        )
        saved = repo.update_item(
            conn,
            item_id,
            workspace_id,
            {"materialized_task_id": task["id"], "backlog_status": "in_progress", "status": "active"},
        )
        repo.create_link(
            conn,
            workspace_id,
            {
                "source_type": "work_item", "source_id": item_id, "relation_type": "materializes",
                "target_type": "task", "target_id": task["id"],
                "metadata": {"materialization": "confirmed"},
            },
            user.id,
        )
    return WorkItem(**saved)


def _validate_dates(data: dict) -> None:
    if data.get("planned_start_at") and data.get("planned_end_at") and data["planned_end_at"] < data["planned_start_at"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A data final não pode ser anterior à inicial.")


def _as_midnight(value):
    if value is None:
        return None
    from datetime import datetime, time, timezone
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def create_link(workspace_id: UUID, payload: WorkLinkCreate, user: CurrentUserResponse) -> WorkLink:
    if payload.source == payload.target:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Um item não pode apontar para si mesmo.")
    with connect() as conn:
        _require_workspace(conn, workspace_id, user)
        for ref, label in ((payload.source, "origem"), (payload.target, "destino")):
            if not repo.entity_exists(conn, workspace_id, ref.type, ref.id):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Entidade de {label} não pertence ao workspace ou não existe.",
                )
        row = repo.create_link(
            conn,
            workspace_id,
            {
                "source_type": payload.source.type,
                "source_id": payload.source.id,
                "relation_type": payload.relation,
                "target_type": payload.target.type,
                "target_id": payload.target.id,
                "metadata": payload.metadata,
            },
            user.id,
        )
    return WorkLink(**row)


def delete_link(workspace_id: UUID, link_id: UUID, user: CurrentUserResponse) -> None:
    with connect() as conn:
        _require_workspace(conn, workspace_id, user)
        deleted = repo.delete_link(conn, link_id, workspace_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relação não encontrada.")
