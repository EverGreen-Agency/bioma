from uuid import UUID

from psycopg.types.json import Jsonb


def list_requests(conn, workspace_id: UUID, limit: int = 30):
    return conn.execute(
        """
        select id, workspace_id, content_type, status, brief, channels, quantity,
          tone, objective, methodology_refs, provider, model, generation_mode,
          output, error_message, created_at, finished_at
        from ai_content_requests
        where workspace_id = %s
        order by created_at desc
        limit %s
        """,
        (workspace_id, limit),
    ).fetchall()


def create_request(
    conn,
    workspace_id: UUID,
    organization_id: UUID,
    user_id: UUID,
    payload: dict,
):
    content_type = payload.get("content_type", "social_posts")
    return conn.execute(
        """
        insert into ai_content_requests (
          workspace_id, organization_id, requested_by, content_type, brief, channels,
          quantity, tone, objective, methodology_refs
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id, workspace_id, content_type, status, brief, channels, quantity,
          tone, objective, methodology_refs, provider, model, generation_mode,
          output, error_message, created_at, finished_at
        """,
        (
            workspace_id,
            organization_id,
            user_id,
            content_type,
            payload["brief"],
            Jsonb(payload["channels"]),
            payload["quantity"],
            payload.get("tone"),
            payload.get("objective"),
            Jsonb(payload.get("methodology_refs", [])),
        ),
    ).fetchone()
