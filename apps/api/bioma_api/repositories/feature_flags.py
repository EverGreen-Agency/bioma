from typing import Any
from uuid import UUID

COLUMNS = "id, organization_id, feature_key, state, note, updated_by, created_at, updated_at"


def list_for_organization(conn, organization_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        f"select {COLUMNS} from organization_feature_flags where organization_id = %s order by feature_key",
        (organization_id,),
    ).fetchall()


def list_all(conn) -> list[dict[str, Any]]:
    return conn.execute(
        f"select {COLUMNS} from organization_feature_flags order by organization_id, feature_key",
    ).fetchall()


def upsert(
    conn,
    organization_id: UUID,
    feature_key: str,
    state: str,
    note: str | None,
    updated_by: UUID,
) -> dict[str, Any]:
    return conn.execute(
        f"""
        insert into organization_feature_flags (organization_id, feature_key, state, note, updated_by)
        values (%s, %s, %s, %s, %s)
        on conflict (organization_id, feature_key)
        do update set state = excluded.state, note = excluded.note,
                      updated_by = excluded.updated_by, updated_at = now()
        returning {COLUMNS}
        """,
        (organization_id, feature_key, state, note, updated_by),
    ).fetchone()


def clear(conn, organization_id: UUID, feature_key: str) -> bool:
    """Remove a exceção e devolve a feature ao default do catálogo em código."""
    row = conn.execute(
        "delete from organization_feature_flags where organization_id = %s and feature_key = %s returning id",
        (organization_id, feature_key),
    ).fetchone()
    return row is not None
