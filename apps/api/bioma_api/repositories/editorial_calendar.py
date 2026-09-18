from uuid import UUID
from psycopg.types.json import Jsonb


def list_calendar_items(conn, workspace_id: UUID, stage: str | None = None, limit: int = 100):
    query = """
        select id, workspace_id, title, content_type, channel, scheduled_at,
               stage, post_text, media_urls, metadata, created_at, updated_at
        from workspace_editorial_calendar
        where workspace_id = %s
    """
    params = [workspace_id]
    if stage:
        query += " and stage = %s"
        params.append(stage)
    query += " order by coalesce(scheduled_at, created_at) desc limit %s"
    params.append(limit)
    return conn.execute(query, params).fetchall()


def create_calendar_item(conn, workspace_id: UUID, payload: dict):
    return conn.execute(
        """
        insert into workspace_editorial_calendar (
          workspace_id, title, content_type, channel, scheduled_at, stage, post_text, media_urls, metadata
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id, workspace_id, title, content_type, channel, scheduled_at,
                  stage, post_text, media_urls, metadata, created_at, updated_at
        """,
        (
            workspace_id,
            payload["title"],
            payload.get("content_type", "social_post"),
            payload.get("channel", "instagram"),
            payload.get("scheduled_at"),
            payload.get("stage", "ideation"),
            payload.get("post_text"),
            Jsonb(payload.get("media_urls", [])),
            Jsonb(payload.get("metadata", {})),
        ),
    ).fetchone()


def update_calendar_stage(conn, workspace_id: UUID, item_id: UUID, stage: str):
    return conn.execute(
        """
        update workspace_editorial_calendar
        set stage = %s, updated_at = now()
        where id = %s and workspace_id = %s
        returning id, workspace_id, title, content_type, channel, scheduled_at,
                  stage, post_text, media_urls, metadata, created_at, updated_at
        """,
        (stage, item_id, workspace_id),
    ).fetchone()


def get_ready_ai_content_request(conn, workspace_id: UUID, request_id: UUID):
    return conn.execute(
        "select id, output, provider, model, generation_mode from ai_content_requests "
        "where id = %s and workspace_id = %s and status = 'ready'",
        (request_id, workspace_id),
    ).fetchone()


def get_calendar_item_for_update(conn, workspace_id: UUID, item_id: UUID):
    return conn.execute(
        "select * from workspace_editorial_calendar where id = %s and workspace_id = %s for update",
        (item_id, workspace_id),
    ).fetchone()


def update_calendar_item(conn, workspace_id: UUID, item_id: UUID, payload: dict):
    return conn.execute(
        """
        update workspace_editorial_calendar
        set title = %s, content_type = %s, channel = %s, scheduled_at = %s,
            post_text = %s, media_urls = %s, updated_at = now()
        where id = %s and workspace_id = %s
        returning id, workspace_id, title, content_type, channel, scheduled_at,
                  stage, post_text, media_urls, metadata, created_at, updated_at
        """,
        (
            payload["title"], payload["content_type"], payload["channel"],
            payload["scheduled_at"], payload["post_text"], Jsonb(payload["media_urls"]),
            item_id, workspace_id,
        ),
    ).fetchone()
