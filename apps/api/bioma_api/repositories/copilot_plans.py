from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

PLAN_COLUMNS = (
    "id, workspace_id, created_by, goal, summary, status, requires_confirmation_count, "
    "approved_by, approved_at, finished_at, error_message, generation_mode, created_at, updated_at"
)
STEP_COLUMNS = (
    "id, plan_id, position, action_name, label, params, why, status, detail, undo_hint, "
    "executed_at, created_at"
)


def create_plan(conn, values: dict[str, Any]) -> dict[str, Any]:
    return conn.execute(
        f"""
        insert into copilot_plans (
          workspace_id, created_by, goal, summary, requires_confirmation_count, generation_mode
        )
        values (%s, %s, %s, %s, %s, %s)
        returning {PLAN_COLUMNS}
        """,
        (
            values.get("workspace_id"),
            values["created_by"],
            values["goal"],
            values["summary"],
            values.get("requires_confirmation_count", 0),
            values.get("generation_mode", "live"),
        ),
    ).fetchone()


def add_step(conn, plan_id: UUID, position: int, values: dict[str, Any]) -> dict[str, Any]:
    return conn.execute(
        f"""
        insert into copilot_plan_steps (plan_id, position, action_name, label, params, why, status)
        values (%s, %s, %s, %s, %s, %s, %s)
        returning {STEP_COLUMNS}
        """,
        (
            plan_id,
            position,
            values["action_name"],
            values["label"],
            Jsonb(values.get("params") or {}),
            values.get("why", ""),
            values.get("status", "pending"),
        ),
    ).fetchone()


def get_plan(conn, plan_id: UUID) -> dict[str, Any] | None:
    return conn.execute(f"select {PLAN_COLUMNS} from copilot_plans where id = %s", (plan_id,)).fetchone()


def list_plans(conn, workspace_id: UUID | None, limit: int = 30) -> list[dict[str, Any]]:
    if workspace_id:
        return conn.execute(
            f"select {PLAN_COLUMNS} from copilot_plans where workspace_id = %s order by created_at desc limit %s",
            (workspace_id, limit),
        ).fetchall()
    return conn.execute(
        f"select {PLAN_COLUMNS} from copilot_plans order by created_at desc limit %s",
        (limit,),
    ).fetchall()


def list_steps(conn, plan_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        f"select {STEP_COLUMNS} from copilot_plan_steps where plan_id = %s order by position",
        (plan_id,),
    ).fetchall()


def approve_plan(conn, plan_id: UUID, approved_by: UUID) -> dict[str, Any] | None:
    """Só aprova o que está pendente — evita re-executar plano já rodado."""
    return conn.execute(
        f"""
        update copilot_plans
        set status = 'approved', approved_by = %s, approved_at = now(), updated_at = now()
        where id = %s and status = 'pending_approval'
        returning {PLAN_COLUMNS}
        """,
        (approved_by, plan_id),
    ).fetchone()


def set_plan_status(conn, plan_id: UUID, status: str, error_message: str | None = None) -> dict[str, Any] | None:
    finished = status in ("completed", "failed", "rejected", "cancelled")
    return conn.execute(
        f"""
        update copilot_plans
        set status = %s,
            error_message = %s,
            finished_at = case when %s then now() else finished_at end,
            updated_at = now()
        where id = %s
        returning {PLAN_COLUMNS}
        """,
        (status, error_message, finished, plan_id),
    ).fetchone()


def update_step(conn, step_id: UUID, values: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"status", "detail", "undo_hint"}
    fields = {key: value for key, value in values.items() if key in allowed}
    if not fields:
        return None
    assignments = ", ".join(f"{key} = %s" for key in fields)
    executed = ", executed_at = now()" if fields.get("status") == "executed" else ""
    return conn.execute(
        f"update copilot_plan_steps set {assignments}{executed} where id = %s returning {STEP_COLUMNS}",
        (*fields.values(), step_id),
    ).fetchone()
