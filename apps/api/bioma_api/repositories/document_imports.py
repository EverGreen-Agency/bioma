from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


COLUMNS = """
  id, workspace_id, project_id, source_name, content_type, content_hash,
  source_size_bytes, extracted_title, extracted_text, extraction_version,
  status, candidates, warnings, materialized_item_ids, created_by,
  materialized_by, materialized_at, created_at, updated_at
"""


def list_for_project(conn, project_id: UUID) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"select {COLUMNS} from project_document_imports where project_id = %s order by created_at desc",
            (project_id,),
        )
        return list(cur.fetchall())


def get(conn, import_id: UUID, *, for_update: bool = False) -> dict[str, Any] | None:
    suffix = " for update" if for_update else ""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"select {COLUMNS} from project_document_imports where id = %s{suffix}", (import_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create(conn, data: dict[str, Any], user_id: UUID) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            insert into project_document_imports (
              workspace_id, project_id, source_name, content_type, content_hash,
              source_size_bytes, extracted_title, extracted_text, extraction_version,
              candidates, warnings, created_by
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (project_id, content_hash) do update
              set updated_at = project_document_imports.updated_at
            returning {COLUMNS}
            """,
            (
                data["workspace_id"], data["project_id"], data["source_name"], data["content_type"],
                data["content_hash"], data["source_size_bytes"], data.get("extracted_title"),
                data["extracted_text"], data["extraction_version"], Jsonb(data["candidates"]),
                Jsonb(data["warnings"]), user_id,
            ),
        )
        return dict(cur.fetchone())


def mark_materialized(conn, import_id: UUID, user_id: UUID, item_ids: list[UUID]) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            update project_document_imports
            set status = 'materialized', materialized_item_ids = %s,
                materialized_by = %s, materialized_at = now(), updated_at = now()
            where id = %s returning {COLUMNS}
            """,
            (Jsonb([str(item_id) for item_id in item_ids]), user_id, import_id),
        )
        return dict(cur.fetchone())
