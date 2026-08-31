from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


_SUMMARY_COLUMNS = """
  research.id, research.workspace_id, research.version, research.sector,
  research.geographic_scope, research.objective, research.selected_focus,
  research.status, research.generation_mode, research.provider, research.model,
  research.token_usage, research.estimated_cost_cents, research.source_count,
  research.error_message, research.completed_at,
  research.created_at, research.updated_at
"""


def lock_workspace(conn, workspace_id: UUID) -> None:
    conn.execute("select id from workspaces where id = %s for update", (workspace_id,)).fetchone()


def next_version(conn, workspace_id: UUID) -> int:
    row = conn.execute(
        "select coalesce(max(version), 0)::int + 1 as version from market_researches where workspace_id = %s",
        (workspace_id,),
    ).fetchone()
    return row["version"]


def create_running(
    conn,
    workspace_id: UUID,
    tenant_organization_id: UUID,
    subject_organization_id: UUID,
    user_id: UUID,
    version: int,
    payload: dict[str, Any],
):
    return conn.execute(
        """
        insert into market_researches (
          workspace_id, tenant_organization_id, subject_organization_id, version,
          sector, geographic_scope, objective, selected_focus, status,
          generation_mode, created_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, 'running', 'manual', %s)
        returning *
        """,
        (
            workspace_id,
            tenant_organization_id,
            subject_organization_id,
            version,
            payload["sector"],
            payload["geographic_scope"],
            payload.get("objective"),
            Jsonb(payload["selected_focus"]),
            user_id,
        ),
    ).fetchone()


def complete_research(conn, research_id: UUID, result: dict[str, Any]):
    return conn.execute(
        """
        update market_researches
        set status = 'completed', generation_mode = %s, provider = %s, model = %s,
          provider_response_id = %s, report = %s, token_usage = %s,
          estimated_cost_cents = %s, source_count = %s, error_message = null,
          completed_at = now(), updated_at = now()
        where id = %s and status = 'running'
        returning *
        """,
        (
            result["generation_mode"],
            result.get("provider"),
            result.get("model"),
            result.get("response_id"),
            Jsonb(result["report"]),
            Jsonb(result.get("token_usage", {})),
            result.get("estimated_cost_cents"),
            len(result.get("sources", [])),
            research_id,
        ),
    ).fetchone()


def fail_research(conn, research_id: UUID, error_message: str) -> None:
    conn.execute(
        """
        update market_researches
        set status = 'failed', error_message = %s, updated_at = now()
        where id = %s and status = 'running'
        """,
        (error_message[:2_000], research_id),
    )


def replace_sources(conn, research_id: UUID, sources: list[dict[str, Any]]) -> None:
    conn.execute("delete from market_research_sources where research_id = %s", (research_id,))
    for source in sources:
        conn.execute(
            """
            insert into market_research_sources (
              research_id, url, title, publisher, publication_date, consulted_at
            ) values (%s, %s, %s, %s, %s, coalesce(%s, now()))
            on conflict (research_id, url) do update set
              title = excluded.title,
              publisher = excluded.publisher,
              publication_date = excluded.publication_date
            """,
            (
                research_id,
                source["url"],
                source.get("title"),
                source.get("publisher"),
                source.get("publication_date"),
                source.get("consulted_at"),
            ),
        )


def list_sources(conn, research_id: UUID):
    return conn.execute(
        """
        select url, title, publisher, publication_date, consulted_at
        from market_research_sources
        where research_id = %s
        order by coalesce(publisher, ''), coalesce(title, ''), url
        """,
        (research_id,),
    ).fetchall()


def list_researches(conn, workspace_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        f"""
        select {_SUMMARY_COLUMNS}
        from market_researches research
        cross join lateral (
          select case
            when %s then 'platform_admin'
            else workspace_access_role(research.workspace_id, %s)
          end as role
        ) access
        where research.workspace_id = %s
          and access.role is not null
        order by research.version desc
        """,
        (is_admin, user_id, workspace_id),
    ).fetchall()


def find_research_context(conn, research_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        f"""
        select {_SUMMARY_COLUMNS}, research.tenant_organization_id,
          research.subject_organization_id, research.report, access.role as access_role
        from market_researches research
        join workspaces workspace on workspace.id = research.workspace_id
        cross join lateral (
          select case
            when %s then 'platform_admin'
            else workspace_access_role(research.workspace_id, %s)
          end as role
        ) access
        where research.id = %s
          and workspace.kind = 'agency_internal'
          and access.role is not null
        """,
        (is_admin, user_id, research_id),
    ).fetchone()
