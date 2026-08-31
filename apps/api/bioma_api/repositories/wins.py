"""Persistência do mural de vitórias."""

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

COLUMNS = """
  id, title, description, category, source, rule_key, dedupe_key, evidence,
  metric_value, metric_unit, benchmark_link, workspace_id, is_ceo,
  credited_user_ids, visibility, pinned, reactions, occurred_at,
  created_by, created_at, updated_at
"""


def create(conn, data: dict[str, Any]) -> dict[str, Any] | None:
    """Insere a vitória. Devolve None quando já existia (dedupe).

    `on conflict do nothing` em vez de erro: o detector roda de novo o tempo
    todo, e colidir é o caso normal, não a exceção.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            insert into wins (
              title, description, category, source, rule_key, dedupe_key, evidence,
              metric_value, metric_unit, benchmark_link, workspace_id, is_ceo,
              credited_user_ids, visibility, occurred_at, created_by
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (dedupe_key) do nothing
            returning {COLUMNS}
            """,
            (
                data["title"],
                data.get("description"),
                data.get("category", "operacao"),
                data.get("source", "manual"),
                data.get("rule_key"),
                data.get("dedupe_key"),
                Jsonb(data.get("evidence") or {}),
                data.get("metric_value"),
                data.get("metric_unit"),
                Jsonb(data["benchmark_link"]) if data.get("benchmark_link") else None,
                data.get("workspace_id"),
                data.get("is_ceo", False),
                Jsonb(data.get("credited_user_ids") or []),
                data.get("visibility", "eg"),
                data.get("occurred_at"),
                data.get("created_by"),
            ),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get(conn, win_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"select {COLUMNS} from wins where id = %s", (win_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_wins(
    conn,
    category: str | None = None,
    workspace_id: UUID | None = None,
    ceo_only: bool = False,
    since: datetime | None = None,
    visibility: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Fixadas primeiro, depois as mais recentes."""
    query = f"select {COLUMNS} from wins"
    clauses: list[str] = []
    params: list[Any] = []
    if category:
        clauses.append("category = %s")
        params.append(category)
    if workspace_id:
        clauses.append("workspace_id = %s")
        params.append(workspace_id)
    if ceo_only:
        clauses.append("is_ceo")
    if since:
        clauses.append("occurred_at >= %s")
        params.append(since)
    if visibility:
        clauses.append("visibility = %s")
        params.append(visibility)
    if clauses:
        query += " where " + " and ".join(clauses)
    query += " order by pinned desc, occurred_at desc limit %s"
    params.append(limit)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def update(conn, win_id: UUID, fields: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"title", "description", "category", "visibility", "pinned", "is_ceo", "occurred_at"}
    updates = {key: value for key, value in fields.items() if key in allowed and value is not None}
    if not updates:
        return get(conn, win_id)
    sets = ", ".join(f"{key} = %s" for key in updates)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"update wins set {sets}, updated_at = now() where id = %s returning {COLUMNS}",
            (*updates.values(), win_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def react(conn, win_id: UUID, emoji: str, user_id: UUID) -> dict[str, Any] | None:
    """Alterna a reação de quem clicou.

    A contagem é derivada da lista de quem reagiu, e não um inteiro incrementado:
    contador solto perde a sincronia na primeira condição de corrida, e aí o
    mural mostra 3 joinhas com dois nomes embaixo.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select reactions from wins where id = %s for update", (win_id,))
        row = cur.fetchone()
        if not row:
            return None
        reactions = dict(row["reactions"] or {})
        people = list(reactions.get(emoji) or [])
        user = str(user_id)
        if user in people:
            people.remove(user)
        else:
            people.append(user)
        if people:
            reactions[emoji] = people
        else:
            reactions.pop(emoji, None)
        cur.execute(
            f"update wins set reactions = %s, updated_at = now() where id = %s returning {COLUMNS}",
            (Jsonb(reactions), win_id),
        )
        return dict(cur.fetchone())


def delete(conn, win_id: UUID) -> bool:
    with conn.cursor() as cur:
        cur.execute("delete from wins where id = %s", (win_id,))
        return cur.rowcount > 0


def last_scan(conn, rule_key: str) -> datetime | None:
    row = conn.execute(
        "select last_scanned_at from win_detector_runs where rule_key = %s", (rule_key,)
    ).fetchone()
    return row["last_scanned_at"] if row else None


def record_scan(conn, rule_key: str, found: int) -> None:
    conn.execute(
        """
        insert into win_detector_runs (rule_key, last_scanned_at, last_found, total_found)
        values (%s, now(), %s, %s)
        on conflict (rule_key) do update set
          last_scanned_at = now(),
          last_found = excluded.last_found,
          total_found = win_detector_runs.total_found + excluded.last_found,
          updated_at = now()
        """,
        (rule_key, found, found),
    )


def summary(conn, days: int = 30) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
              count(*) as total,
              count(*) filter (where source = 'automatic') as automatic,
              count(*) filter (where source = 'manual') as manual,
              count(*) filter (where is_ceo) as ceo,
              count(*) filter (where occurred_at >= now() - interval '7 days') as last_7_days
            from wins
            where occurred_at >= now() - make_interval(days => %s)
            """,
            (days,),
        )
        result = dict(cur.fetchone())
        cur.execute(
            """
            select category, count(*) as total
            from wins
            where occurred_at >= now() - make_interval(days => %s)
            group by category order by total desc
            """,
            (days,),
        )
        result["by_category"] = [dict(row) for row in cur.fetchall()]
    return result
