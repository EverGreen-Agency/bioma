from typing import Any
from uuid import UUID

COLUMNS = (
    "id, workspace_id, title, need, evidence, client_deliverable, status, "
    "proposed_by, reviewed_by, reviewed_at, review_note, task_id, created_at, updated_at"
)


def create(conn, values: dict[str, Any]) -> dict[str, Any]:
    return conn.execute(
        f"""
        insert into improvement_requests (
          workspace_id, title, need, evidence, client_deliverable, proposed_by
        )
        values (%s, %s, %s, %s, %s, %s)
        returning {COLUMNS}
        """,
        (
            values.get("workspace_id"),
            values["title"],
            values["need"],
            values.get("evidence"),
            bool(values.get("client_deliverable")),
            values.get("proposed_by"),
        ),
    ).fetchone()


def list_requests(conn, status: str | None = None, workspace_id: UUID | None = None) -> list[dict[str, Any]]:
    clauses = ["1 = 1"]
    params: list[Any] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if workspace_id:
        clauses.append("workspace_id = %s")
        params.append(workspace_id)
    return conn.execute(
        f"select {COLUMNS} from improvement_requests where {' and '.join(clauses)} order by created_at desc",
        tuple(params),
    ).fetchall()


def get(conn, request_id: UUID) -> dict[str, Any] | None:
    return conn.execute(f"select {COLUMNS} from improvement_requests where id = %s", (request_id,)).fetchone()


def mark_converted(conn, request_id: UUID, task_id: UUID, reviewed_by: UUID, note: str | None) -> dict[str, Any] | None:
    """Só converte o que está pendente — evita gerar duas tarefas para a mesma
    requisição se alguém clicar duas vezes."""
    return conn.execute(
        f"""
        update improvement_requests
        set status = 'converted', task_id = %s, reviewed_by = %s,
            reviewed_at = now(), review_note = %s, updated_at = now()
        where id = %s and status = 'pending'
        returning {COLUMNS}
        """,
        (task_id, reviewed_by, note, request_id),
    ).fetchone()


def reject(conn, request_id: UUID, reviewed_by: UUID, note: str | None) -> dict[str, Any] | None:
    return conn.execute(
        f"""
        update improvement_requests
        set status = 'rejected', reviewed_by = %s, reviewed_at = now(),
            review_note = %s, updated_at = now()
        where id = %s and status = 'pending'
        returning {COLUMNS}
        """,
        (reviewed_by, note, request_id),
    ).fetchone()
