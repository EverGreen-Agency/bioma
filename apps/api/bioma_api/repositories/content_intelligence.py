from datetime import date
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


def list_recent_posts(conn, workspace_id: UUID, period_start: date, period_end: date, limit: int = 200) -> list[dict]:
    return conn.execute(
        """
        select id, ig_media_id, permalink, media_type, caption, posted_at, thumbnail_url,
               reach, impressions, likes, comments, shares, saved, plays,
               avg_watch_time_seconds, transcript, source_script_id
        from workspace_instagram_posts
        where workspace_id = %s and posted_at between %s and %s
        order by posted_at desc
        limit %s
        """,
        (workspace_id, period_start, period_end, limit),
    ).fetchall()


def script_performance_scoreboard(conn, workspace_id: UUID, period_start: date, period_end: date) -> dict:
    """Compara posts que nasceram de roteiro da IA com os demais, no periodo.

    Media por post (nao soma) para nao premiar o grupo que tem mais posts.
    """
    row = conn.execute(
        """
        select
          count(*) filter (where source_script_id is not null) as ai_posts,
          count(*) filter (where source_script_id is null) as other_posts,
          avg(reach) filter (where source_script_id is not null) as ai_avg_reach,
          avg(reach) filter (where source_script_id is null) as other_avg_reach,
          avg(likes + comments + shares + saved) filter (where source_script_id is not null) as ai_avg_engagement,
          avg(likes + comments + shares + saved) filter (where source_script_id is null) as other_avg_engagement,
          avg(saved) filter (where source_script_id is not null) as ai_avg_saved,
          avg(saved) filter (where source_script_id is null) as other_avg_saved
        from workspace_instagram_posts
        where workspace_id = %s and posted_at between %s and %s
        """,
        (workspace_id, period_start, period_end),
    ).fetchone()

    per_script = conn.execute(
        """
        select s.id as script_id, s.title, s.theme, s.suggested_format,
               count(p.id) as posts,
               coalesce(avg(p.reach), 0) as avg_reach,
               coalesce(avg(p.likes + p.comments + p.shares + p.saved), 0) as avg_engagement
        from workspace_content_scripts s
        join workspace_instagram_posts p
          on p.source_script_id = s.id and p.workspace_id = s.workspace_id
        where s.workspace_id = %s and p.posted_at between %s and %s
        group by s.id, s.title, s.theme, s.suggested_format
        order by avg_engagement desc
        limit 20
        """,
        (workspace_id, period_start, period_end),
    ).fetchall()

    return {"totals": dict(row or {}), "per_script": [dict(item) for item in per_script]}


def get_post(conn, workspace_id: UUID, post_id: UUID) -> dict | None:
    return conn.execute(
        """
        select id, ig_media_id, permalink, media_type, caption, posted_at, thumbnail_url,
               reach, impressions, likes, comments, shares, saved, plays,
               avg_watch_time_seconds, transcript, source_script_id
        from workspace_instagram_posts
        where workspace_id = %s and id = %s
        """,
        (workspace_id, post_id),
    ).fetchone()


def link_post_to_script(conn, workspace_id: UUID, post_id: UUID, script_id: UUID) -> dict | None:
    return conn.execute(
        """
        update workspace_instagram_posts set source_script_id = %s, updated_at = now()
        where workspace_id = %s and id = %s
        returning id, ig_media_id, permalink, media_type, caption, posted_at, thumbnail_url,
                  reach, impressions, likes, comments, shares, saved, plays,
                  avg_watch_time_seconds, transcript, source_script_id
        """,
        (script_id, workspace_id, post_id),
    ).fetchone()


def insert_retrospective(
    conn,
    workspace_id: UUID,
    client_id: UUID | None,
    period_start: date,
    period_end: date,
    posts_analyzed: int,
    generation_mode: str,
    output_data: dict[str, Any],
    token_usage: dict[str, Any],
    estimated_cost_cents: int,
    created_by: UUID | None,
) -> dict:
    return conn.execute(
        """
        insert into workspace_content_retrospectives (
          workspace_id, client_id, period_start, period_end, posts_analyzed,
          generation_mode, output_data, token_usage, estimated_cost_cents, created_by
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id, period_start, period_end, posts_analyzed, generation_mode,
                  output_data, token_usage, estimated_cost_cents, created_at
        """,
        (
            workspace_id, client_id, period_start, period_end, posts_analyzed,
            generation_mode, Jsonb(output_data), Jsonb(token_usage), estimated_cost_cents, created_by,
        ),
    ).fetchone()


def get_latest_retrospective(conn, workspace_id: UUID) -> dict | None:
    return conn.execute(
        """
        select id, period_start, period_end, posts_analyzed, generation_mode,
               output_data, token_usage, estimated_cost_cents, created_at
        from workspace_content_retrospectives
        where workspace_id = %s
        order by created_at desc
        limit 1
        """,
        (workspace_id,),
    ).fetchone()


def upsert_hook_analyses(conn, workspace_id: UUID, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    sql = """
        insert into workspace_content_hook_analyses (
          workspace_id, post_id, source, hook_text, hook_pattern,
          effectiveness_score, analysis_notes, raw_output
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (post_id, source) do update set
          hook_text = excluded.hook_text,
          hook_pattern = excluded.hook_pattern,
          effectiveness_score = excluded.effectiveness_score,
          analysis_notes = excluded.analysis_notes,
          raw_output = excluded.raw_output
    """
    count = 0
    for row in rows:
        conn.execute(
            sql,
            (
                workspace_id,
                row["post_id"],
                row["source"],
                row.get("hook_text"),
                row.get("hook_pattern"),
                row.get("effectiveness_score"),
                row.get("analysis_notes"),
                Jsonb(row.get("raw_output", {})),
            ),
        )
        count += 1
    return count


def list_hook_bank(conn, workspace_id: UUID, limit: int = 100) -> list[dict]:
    return conn.execute(
        """
        select h.id, h.post_id, h.source, h.hook_text, h.hook_pattern,
               h.effectiveness_score, h.analysis_notes, h.created_at
        from workspace_content_hook_analyses h
        where h.workspace_id = %s
        order by h.effectiveness_score desc nulls last, h.created_at desc
        limit %s
        """,
        (workspace_id, limit),
    ).fetchall()


def insert_scripts(
    conn,
    workspace_id: UUID,
    client_id: UUID | None,
    retrospective_id: UUID | None,
    generation_mode: str,
    created_by: UUID | None,
    scripts: list[dict[str, Any]],
) -> list[dict]:
    rows = []
    for script in scripts:
        row = conn.execute(
            """
            insert into workspace_content_scripts (
              workspace_id, client_id, retrospective_id, title, theme, hook_opening,
              script_body, suggested_format, cta, rationale, generation_mode, created_by
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning id, retrospective_id, title, theme, hook_opening, script_body,
                      suggested_format, cta, rationale, status, scheduled_for,
                      generation_mode, created_at, updated_at
            """,
            (
                workspace_id, client_id, retrospective_id,
                script["titulo"], script.get("tema"), script.get("gancho_abertura"),
                script["roteiro_completo"], script.get("formato_sugerido"), script.get("cta"),
                script.get("justificativa"), generation_mode, created_by,
            ),
        ).fetchone()
        rows.append(row)
    return rows


def list_scripts(conn, workspace_id: UUID, status: str | None = None, limit: int = 100) -> list[dict]:
    if status:
        return conn.execute(
            """
            select id, retrospective_id, title, theme, hook_opening, script_body,
                   suggested_format, cta, rationale, status, scheduled_for,
                   generation_mode, created_at, updated_at
            from workspace_content_scripts
            where workspace_id = %s and status = %s
            order by coalesce(scheduled_for, created_at::date) asc
            limit %s
            """,
            (workspace_id, status, limit),
        ).fetchall()
    return conn.execute(
        """
        select id, retrospective_id, title, theme, hook_opening, script_body,
               suggested_format, cta, rationale, status, scheduled_for,
               generation_mode, created_at, updated_at
        from workspace_content_scripts
        where workspace_id = %s
        order by coalesce(scheduled_for, created_at::date) asc
        limit %s
        """,
        (workspace_id, limit),
    ).fetchall()


def get_script(conn, workspace_id: UUID, script_id: UUID) -> dict | None:
    return conn.execute(
        """
        select id, retrospective_id, title, theme, hook_opening, script_body,
               suggested_format, cta, rationale, status, scheduled_for,
               generation_mode, created_at, updated_at
        from workspace_content_scripts
        where workspace_id = %s and id = %s
        """,
        (workspace_id, script_id),
    ).fetchone()


def update_script(conn, workspace_id: UUID, script_id: UUID, patch: dict[str, Any]) -> dict | None:
    if not patch:
        return get_script(conn, workspace_id, script_id)
    assignments = ", ".join(f"{key} = %s" for key in patch)
    values = list(patch.values())
    return conn.execute(
        f"""
        update workspace_content_scripts set {assignments}, updated_at = now()
        where workspace_id = %s and id = %s
        returning id, retrospective_id, title, theme, hook_opening, script_body,
                  suggested_format, cta, rationale, status, scheduled_for,
                  generation_mode, created_at, updated_at
        """,
        (*values, workspace_id, script_id),
    ).fetchone()
