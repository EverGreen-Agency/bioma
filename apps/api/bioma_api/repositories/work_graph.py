from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


WORK_ITEM_COLUMNS = """
  id, workspace_id, project_id, kind, title, summary, status, external_ref,
  backlog_status, priority, rank, acceptance_criteria, definition_of_done,
  story_points, planned_start_at, planned_end_at, source_document_import_id,
  materialized_task_id, metadata, created_by, created_at, updated_at
"""
WORK_LINK_COLUMNS = """
  id, workspace_id, source_type, source_id, relation_type, target_type,
  target_id, metadata, created_by, created_at
"""


def list_items(conn, workspace_id: UUID, project_id: UUID | None = None) -> list[dict[str, Any]]:
    query = f"select {WORK_ITEM_COLUMNS} from work_items where workspace_id = %s"
    params: list[Any] = [workspace_id]
    if project_id:
        query += " and project_id = %s"
        params.append(project_id)
    query += " order by updated_at desc, id"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def create_item(conn, workspace_id: UUID, data: dict[str, Any], user_id: UUID) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            insert into work_items (
              workspace_id, project_id, kind, title, summary, status,
              external_ref, backlog_status, priority, rank, acceptance_criteria,
              definition_of_done, story_points, planned_start_at, planned_end_at,
              source_document_import_id, metadata, created_by
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning {WORK_ITEM_COLUMNS}
            """,
            (
                workspace_id, data.get("project_id"), data["kind"], data["title"],
                data.get("summary"), data.get("status", "draft"), data.get("external_ref"),
                data.get("backlog_status", "candidate"), data.get("priority", "medium"),
                data.get("rank", 0), data.get("acceptance_criteria"), data.get("definition_of_done"),
                data.get("story_points"), data.get("planned_start_at"), data.get("planned_end_at"),
                data.get("source_document_import_id"), Jsonb(data.get("metadata") or {}), user_id,
            ),
        )
        return dict(cur.fetchone())


def update_item(conn, item_id: UUID, workspace_id: UUID, fields: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {
        "title", "summary", "status", "external_ref", "backlog_status", "priority", "rank",
        "acceptance_criteria", "definition_of_done", "story_points", "planned_start_at",
        "planned_end_at", "materialized_task_id", "metadata",
    }
    selected = [(key, value) for key, value in fields.items() if key in allowed]
    if not selected:
        return get_item(conn, item_id, workspace_id)
    assignments = ", ".join(f"{key} = %s" for key, _ in selected)
    values = [Jsonb(value) if key == "metadata" else value for key, value in selected]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            update work_items set {assignments}, updated_at = now()
            where id = %s and workspace_id = %s
            returning {WORK_ITEM_COLUMNS}
            """,
            (*values, item_id, workspace_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_item(conn, item_id: UUID, workspace_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"select {WORK_ITEM_COLUMNS} from work_items where id = %s and workspace_id = %s",
            (item_id, workspace_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_links(conn, workspace_id: UUID) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"select {WORK_LINK_COLUMNS} from work_entity_links where workspace_id = %s order by created_at, id",
            (workspace_id,),
        )
        return list(cur.fetchall())


def create_link(conn, workspace_id: UUID, data: dict[str, Any], user_id: UUID) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            insert into work_entity_links (
              workspace_id, source_type, source_id, relation_type, target_type,
              target_id, metadata, created_by
            ) values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (workspace_id, source_type, source_id, relation_type, target_type, target_id)
            do update set metadata = excluded.metadata
            returning {WORK_LINK_COLUMNS}
            """,
            (
                workspace_id, data["source_type"], data["source_id"], data["relation_type"],
                data["target_type"], data["target_id"], Jsonb(data.get("metadata") or {}), user_id,
            ),
        )
        return dict(cur.fetchone())


def delete_link(conn, link_id: UUID, workspace_id: UUID) -> bool:
    row = conn.execute(
        "delete from work_entity_links where id = %s and workspace_id = %s returning id",
        (link_id, workspace_id),
    ).fetchone()
    return row is not None


def entity_exists(conn, workspace_id: UUID, entity_type: str, entity_id: UUID) -> bool:
    # Consultas fixas por tipo: o nome da tabela nunca vem do cliente.
    queries = {
        "workspace": "select 1 from workspaces where id = %s and id = %s",
        "project": "select 1 from projects where id = %s and workspace_id = %s",
        "opportunity": "select 1 from opportunity_radar where id = %s and workspace_id = %s",
        "proposal": """
            select 1 from commercial_proposals p
            left join opportunity_radar o on o.id = p.opportunity_id
            where p.id = %s and coalesce(p.workspace_id, o.workspace_id) = %s
        """,
        "task": """
            select 1 from eg_tasks t
            left join eg_task_lists l on l.id = t.list_id
            where t.id = %s and coalesce(t.workspace_id, l.workspace_id) = %s
        """,
        "document": """
            select 1 from project_documents d
            join projects p on p.id = d.project_id
            where d.id = %s and p.workspace_id = %s
        """,
        "document_import": """
            select 1 from project_document_imports d
            where d.id = %s and d.workspace_id = %s
        """,
        "artifact": """
            select 1 from artifacts a
            join workspaces w on w.subject_organization_id = a.organization_id
            where a.id = %s and w.id = %s
        """,
        "work_item": "select 1 from work_items where id = %s and workspace_id = %s",
    }
    query = queries.get(entity_type)
    return bool(query and conn.execute(query, (entity_id, workspace_id)).fetchone())
