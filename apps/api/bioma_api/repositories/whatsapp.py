from uuid import UUID
from psycopg.types.json import Jsonb


def get_provider_config(conn, workspace_id: UUID, provider_type: str):
    return conn.execute(
        """
        select id, workspace_id, provider_type, api_url, api_token,
               instance_name, phone_number, status, metadata, created_at, updated_at
        from workspace_whatsapp_providers
        where workspace_id = %s and provider_type = %s
        """,
        (workspace_id, provider_type),
    ).fetchone()


def list_provider_configs(conn, workspace_id: UUID):
    return conn.execute(
        """
        select id, workspace_id, provider_type, api_url, api_token,
               instance_name, phone_number, status, metadata, created_at, updated_at
        from workspace_whatsapp_providers
        where workspace_id = %s
        order by created_at desc
        """,
        (workspace_id,),
    ).fetchall()


def upsert_provider_config(conn, workspace_id: UUID, payload: dict):
    return conn.execute(
        """
        insert into workspace_whatsapp_providers (
          workspace_id, provider_type, api_url, api_token,
          instance_name, phone_number, status, metadata
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (workspace_id, provider_type) do update set
          api_url = excluded.api_url,
          api_token = excluded.api_token,
          instance_name = excluded.instance_name,
          phone_number = excluded.phone_number,
          status = excluded.status,
          metadata = excluded.metadata,
          updated_at = now()
        returning id, workspace_id, provider_type, api_url, api_token,
                  instance_name, phone_number, status, metadata, created_at, updated_at
        """,
        (
            workspace_id,
            payload["provider_type"],
            payload.get("api_url"),
            payload.get("api_token"),
            payload.get("instance_name"),
            payload.get("phone_number"),
            payload.get("status", "active"),
            Jsonb(payload.get("metadata", {})),
        ),
    ).fetchone()


def log_message(conn, workspace_id: UUID, payload: dict):
    return conn.execute(
        """
        insert into workspace_whatsapp_message_logs (
          workspace_id, provider_type, to_number, message_type,
          payload, status, error_message
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        returning id, workspace_id, provider_type, to_number, message_type,
                  payload, status, error_message, sent_at
        """,
        (
            workspace_id,
            payload["provider_type"],
            payload["to_number"],
            payload.get("message_type", "text"),
            Jsonb(payload.get("payload", {})),
            payload.get("status", "sent"),
            payload.get("error_message"),
        ),
    ).fetchone()


def list_logs(conn, workspace_id: UUID, limit: int = 50):
    return conn.execute(
        """
        select id, workspace_id, provider_type, to_number, message_type,
               payload, status, error_message, sent_at
        from workspace_whatsapp_message_logs
        where workspace_id = %s
        order by sent_at desc
        limit %s
        """,
        (workspace_id, limit),
    ).fetchall()
