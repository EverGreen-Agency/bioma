from uuid import UUID
from psycopg.types.json import Jsonb


def list_squad_definitions(conn, workspace_id: UUID):
    return conn.execute(
        """
        select id, workspace_id, pilar, squad_slug, squad_name,
               description, agents_config, pipeline_yaml, status, created_at, updated_at
        from workspace_squad_definitions
        where workspace_id = %s
        order by pilar, squad_name
        """,
        (workspace_id,),
    ).fetchall()


def get_squad_definition(conn, workspace_id: UUID, squad_slug: str):
    return conn.execute(
        """
        select id, workspace_id, pilar, squad_slug, squad_name,
               description, agents_config, pipeline_yaml, status, created_at, updated_at
        from workspace_squad_definitions
        where workspace_id = %s and squad_slug = %s
        """,
        (workspace_id, squad_slug),
    ).fetchone()


def upsert_squad_definition(conn, workspace_id: UUID, payload: dict):
    return conn.execute(
        """
        insert into workspace_squad_definitions (
          workspace_id, pilar, squad_slug, squad_name, description, agents_config, pipeline_yaml, status
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (workspace_id, squad_slug) do update set
          squad_name = excluded.squad_name,
          description = excluded.description,
          agents_config = excluded.agents_config,
          pipeline_yaml = excluded.pipeline_yaml,
          status = excluded.status,
          updated_at = now()
        returning id, workspace_id, pilar, squad_slug, squad_name,
                  description, agents_config, pipeline_yaml, status, created_at, updated_at
        """,
        (
            workspace_id,
            payload["pilar"],
            payload["squad_slug"],
            payload["squad_name"],
            payload.get("description"),
            Jsonb(payload.get("agents_config", [])),
            payload.get("pipeline_yaml"),
            payload.get("status", "active"),
        ),
    ).fetchone()


def create_execution(conn, workspace_id: UUID, payload: dict):
    return conn.execute(
        """
        insert into workspace_squad_executions (
          workspace_id, squad_id, pilar, squad_name, triggered_by, status,
          generation_mode, input_data, output_data, token_usage,
          estimated_cost_cents, execution_logs, completed_at
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id, workspace_id, squad_id, pilar, squad_name, triggered_by,
                  status, generation_mode, input_data, output_data, token_usage,
                  estimated_cost_cents, execution_logs, started_at, completed_at
        """,
        (
            workspace_id,
            payload.get("squad_id"),
            payload["pilar"],
            payload["squad_name"],
            payload.get("triggered_by", "manual"),
            payload.get("status", "completed"),
            payload.get("generation_mode", "manual"),
            Jsonb(payload.get("input_data", {})),
            Jsonb(payload.get("output_data", {})),
            Jsonb(payload.get("token_usage", {})),
            payload.get("estimated_cost_cents", 0),
            Jsonb(payload.get("execution_logs", [])),
            payload.get("completed_at"),
        ),
    ).fetchone()


def list_executions(conn, workspace_id: UUID, limit: int = 50):
    return conn.execute(
        """
        select id, workspace_id, squad_id, pilar, squad_name, triggered_by,
               status, generation_mode, input_data, output_data, token_usage,
               estimated_cost_cents, execution_logs, started_at, completed_at
        from workspace_squad_executions
        where workspace_id = %s
        order by started_at desc
        limit %s
        """,
        (workspace_id, limit),
    ).fetchall()


def get_finops_summary(conn, workspace_id: UUID):
    row = conn.execute(
        """
        select
          coalesce(sum((token_usage->>'total_tokens')::int), 0) as total_tokens,
          coalesce(sum((token_usage->>'prompt_tokens')::int), 0) as prompt_tokens,
          coalesce(sum((token_usage->>'completion_tokens')::int), 0) as completion_tokens,
          coalesce(sum(estimated_cost_cents), 0) as total_cost_cents,
          count(*) as total_executions
        from workspace_squad_executions
        where workspace_id = %s
        """,
        (workspace_id,),
    ).fetchone()
    return dict(row) if row else {
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_cost_cents": 0,
        "total_executions": 0,
    }
