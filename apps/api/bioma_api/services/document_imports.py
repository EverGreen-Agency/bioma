from datetime import date, datetime, time, timezone
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_workspace_capability
from bioma_api.db import connect
from bioma_api.document_ingestion import EXTRACTION_VERSION, extract_project_html
from bioma_api.repositories import document_imports as repo
from bioma_api.repositories import projects as project_repo
from bioma_api.repositories import tasks as tasks_repo
from bioma_api.repositories import work_graph as work_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.document_imports import ProjectDocumentImport, ProjectDocumentImportMaterialize


MAX_HTML_BYTES = 2_000_000


def list_imports(project_id: UUID, user: CurrentUserResponse) -> list[ProjectDocumentImport]:
    with connect() as conn:
        _project(conn, project_id, user, "manage_work")
        rows = repo.list_for_project(conn, project_id)
    return [ProjectDocumentImport(**row) for row in rows]


def preview_import(
    project_id: UUID,
    source_name: str,
    content_type: str,
    content: bytes,
    user: CurrentUserResponse,
) -> ProjectDocumentImport:
    if not content or len(content) > MAX_HTML_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="O HTML deve ter entre 1 byte e 2 MB.")
    normalized_content_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_content_type not in {"text/html", "application/xhtml+xml", "application/octet-stream"} and not source_name.lower().endswith((".html", ".htm")):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Envie um arquivo HTML.")
    decoded = content.decode("utf-8-sig", errors="replace")
    extraction = extract_project_html(decoded)
    with connect() as conn:
        project = _project(conn, project_id, user, "manage_work")
        row = repo.create(
            conn,
            {
                "workspace_id": project["workspace_id"],
                "project_id": project_id,
                "source_name": source_name,
                "content_type": content_type or "text/html",
                "content_hash": sha256(content).hexdigest(),
                "source_size_bytes": len(content),
                "extracted_title": extraction["title"],
                "extracted_text": extraction["text"],
                "extraction_version": EXTRACTION_VERSION,
                "candidates": [_json_candidate(item) for item in extraction["candidates"]],
                "warnings": extraction["warnings"],
            },
            user.id,
        )
        project_repo.write_audit(
            conn,
            user.id,
            project["organization_id"],
            "project.document_import_previewed",
            {"project_id": str(project_id), "import_id": str(row["id"]), "candidates": len(row["candidates"])},
        )
    return ProjectDocumentImport(**row)


def materialize_import(
    import_id: UUID,
    payload: ProjectDocumentImportMaterialize,
    user: CurrentUserResponse,
) -> ProjectDocumentImport:
    requested = list(dict.fromkeys(payload.candidate_ids))
    with connect() as conn:
        imported = repo.get(conn, import_id, for_update=True)
        if not imported:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importação não encontrada.")
        project = _project(conn, imported["project_id"], user, "manage_work")
        if imported["status"] == "materialized":
            return ProjectDocumentImport(**imported)
        by_id = {candidate["id"]: candidate for candidate in imported["candidates"]}
        missing = [candidate_id for candidate_id in requested if candidate_id not in by_id]
        if missing:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Há candidatos que não pertencem a esta importação.")
        item_ids: list[UUID] = []
        for rank, candidate_id in enumerate(requested, start=1):
            candidate = by_id[candidate_id]
            item = work_repo.create_item(
                conn,
                imported["workspace_id"],
                {
                    "project_id": imported["project_id"],
                    "kind": candidate["kind"],
                    "title": candidate["title"],
                    "summary": candidate.get("summary"),
                    "status": "active",
                    "external_ref": candidate.get("metadata", {}).get("source_url"),
                    "backlog_status": "backlog",
                    "priority": candidate.get("priority", "medium"),
                    "rank": rank,
                    "acceptance_criteria": candidate.get("acceptance_criteria"),
                    "definition_of_done": candidate.get("definition_of_done"),
                    "planned_start_at": candidate.get("planned_start_at"),
                    "planned_end_at": candidate.get("planned_end_at"),
                    "source_document_import_id": import_id,
                    "metadata": {**candidate.get("metadata", {}), "source_excerpt": candidate["source_excerpt"]},
                },
                user.id,
            )
            item_ids.append(item["id"])
            work_repo.create_link(
                conn,
                imported["workspace_id"],
                {
                    "source_type": "work_item", "source_id": item["id"], "relation_type": "derives_from",
                    "target_type": "document_import", "target_id": import_id,
                    "metadata": {"candidate_id": candidate_id},
                },
                user.id,
            )
            if payload.create_tasks:
                _create_task(conn, imported["workspace_id"], imported["project_id"], item, candidate, user.id)
        saved = repo.mark_materialized(conn, import_id, user.id, item_ids)
        project_repo.write_audit(
            conn,
            user.id,
            project["organization_id"],
            "project.document_import_materialized",
            {
                "project_id": str(imported["project_id"]), "import_id": str(import_id),
                "work_items": len(item_ids), "tasks_created": payload.create_tasks,
            },
        )
    return ProjectDocumentImport(**saved)


def _project(conn, project_id: UUID, user: CurrentUserResponse, capability: str):
    project = project_repo.find_project_context(conn, project_id, is_platform_admin(user), user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    require_workspace_capability(project, user, capability)
    return project


def _json_candidate(candidate: dict) -> dict:
    return {
        **candidate,
        "planned_start_at": candidate["planned_start_at"].isoformat() if candidate.get("planned_start_at") else None,
        "planned_end_at": candidate["planned_end_at"].isoformat() if candidate.get("planned_end_at") else None,
    }


def _at_midnight(value: str | date | None):
    if not value:
        return None
    resolved = date.fromisoformat(value) if isinstance(value, str) else value
    return datetime.combine(resolved, time.min, tzinfo=timezone.utc)


def _create_task(conn, workspace_id: UUID, project_id: UUID, item: dict, candidate: dict, user_id: UUID) -> None:
    priority = {"critical": "Alta", "high": "Alta", "medium": "Média", "low": "Baixa"}[candidate.get("priority", "medium")]
    task = tasks_repo.create_task_in_workspace(
        conn,
        workspace_id,
        {
            "title": candidate["title"], "description": candidate.get("summary"),
            "acceptance_criteria": candidate.get("acceptance_criteria"),
            "definition_of_done": candidate.get("definition_of_done"),
            "status": "A fazer", "group_status": "NOT_STARTED", "priority": priority,
            "start_date": _at_midnight(candidate.get("planned_start_at")),
            "due_date": _at_midnight(candidate.get("planned_end_at")),
            "recurrence": "none", "client_visible": False, "project_id": project_id,
        },
    )
    work_repo.update_item(
        conn, item["id"], workspace_id,
        {"materialized_task_id": task["id"], "backlog_status": "in_progress"},
    )
    work_repo.create_link(
        conn,
        workspace_id,
        {
            "source_type": "work_item", "source_id": item["id"], "relation_type": "materializes",
            "target_type": "task", "target_id": task["id"], "metadata": {"source": "document_import"},
        },
        user_id,
    )
