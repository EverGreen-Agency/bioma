"""Persistência dos anexos do copiloto."""

from typing import Any
from uuid import UUID

from psycopg.rows import dict_row

COLUMNS = """
  id, thread_id, user_id, file_name, content_type, size_bytes, storage_key, kind,
  extraction_status, extraction_error, extracted_text, truncated_chars, created_at
"""


def create(conn, data: dict[str, Any]) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            insert into copilot_attachments (
              thread_id, user_id, file_name, content_type, size_bytes, storage_key, kind,
              extraction_status, extraction_error, extracted_text, truncated_chars
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning {COLUMNS}
            """,
            (
                data.get("thread_id"),
                data["user_id"],
                data["file_name"],
                data["content_type"],
                data["size_bytes"],
                data["storage_key"],
                data["kind"],
                data["extraction_status"],
                data.get("extraction_error"),
                data.get("extracted_text"),
                data.get("truncated_chars"),
            ),
        )
        return dict(cur.fetchone())


def get(conn, attachment_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"select {COLUMNS} from copilot_attachments where id = %s", (attachment_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_by_ids(conn, attachment_ids: list[UUID], user_id: UUID) -> list[dict[str, Any]]:
    """Só os anexos do próprio usuário.

    Filtrar por `user_id` aqui, e não na chamada, fecha a porta de pedir o anexo
    de outra pessoa passando o id na mensagem.
    """
    if not attachment_ids:
        return []
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"select {COLUMNS} from copilot_attachments where id = any(%s) and user_id = %s order by created_at",
            (attachment_ids, user_id),
        )
        return list(cur.fetchall())


def list_by_thread(conn, thread_id: UUID) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"select {COLUMNS} from copilot_attachments where thread_id = %s order by created_at",
            (thread_id,),
        )
        return list(cur.fetchall())


def bind_to_thread(conn, attachment_ids: list[UUID], thread_id: UUID) -> None:
    """Amarra à conversa os anexos enviados antes dela existir.

    O arquivo é enviado enquanto a pessoa ainda está escrevendo — não dá para
    exigir que a thread exista antes. Ele nasce solto e é adotado no envio.
    """
    if not attachment_ids:
        return
    with conn.cursor() as cur:
        cur.execute(
            "update copilot_attachments set thread_id = %s where id = any(%s) and thread_id is null",
            (thread_id, attachment_ids),
        )


def set_extraction(conn, attachment_id: UUID, status: str, text: str | None, error: str | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            update copilot_attachments
            set extraction_status = %s, extracted_text = %s, extraction_error = %s
            where id = %s
            """,
            (status, text, error, attachment_id),
        )


def delete(conn, attachment_id: UUID, user_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"delete from copilot_attachments where id = %s and user_id = %s returning {COLUMNS}",
            (attachment_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
