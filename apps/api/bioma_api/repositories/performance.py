from datetime import date
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


# Conexão pertence ao WORKSPACE desde a migração 0087. `client_id` continua
# gravado (as métricas diárias agrupam por cliente), mas não é mais a chave —
# o que permite a Operação EG conectar mídia sem um registro em `clients`.


def list_connections(conn, workspace_id: UUID):
    return conn.execute(
        """
        select id, workspace_id, client_id, provider, external_account_id, external_parent_id, display_name,
               status, (credentials_ref is not null) as credentials_configured,
               last_synced_at, last_error_at, last_error_message,
               metadata, created_at, updated_at
        from performance_connections
        where workspace_id = %s
        order by provider asc, created_at asc
        """,
        (workspace_id,),
    ).fetchall()


def create_connection(
    conn, workspace_id: UUID, client_id: UUID | None, organization_id: UUID, payload: dict[str, Any]
) -> UUID:
    return conn.execute(
        """
        insert into performance_connections (
          workspace_id, client_id, organization_id, provider, external_account_id, external_parent_id,
          display_name, status, credentials_ref, metadata
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (workspace_id, provider, external_account_id)
        do update set
          client_id = excluded.client_id,
          organization_id = excluded.organization_id,
          external_parent_id = excluded.external_parent_id,
          display_name = excluded.display_name,
          status = excluded.status,
          credentials_ref = excluded.credentials_ref,
          metadata = excluded.metadata,
          updated_at = now()
        returning id
        """,
        (
            workspace_id,
            client_id,
            organization_id,
            payload["provider"],
            payload["external_account_id"],
            payload.get("external_parent_id"),
            payload.get("display_name"),
            payload.get("status", "active"),
            payload.get("credentials_ref"),
            Jsonb(payload.get("metadata", {})),
        ),
    ).fetchone()["id"]


def update_connection(conn, workspace_id: UUID, connection_id: UUID, updates: dict[str, Any]) -> bool:
    if not updates:
        return True

    values = dict(updates)
    if "metadata" in values:
        values["metadata"] = Jsonb(values["metadata"])

    set_clause = ", ".join([f"{column} = %s" for column in values])
    params = list(values.values()) + [connection_id, workspace_id]
    updated = conn.execute(
        f"""
        update performance_connections
        set {set_clause}, updated_at = now()
        where id = %s and workspace_id = %s
        returning id
        """,
        params,
    ).fetchone()
    return updated is not None


def list_recent_sync_runs(conn, workspace_id, client_id, limit: int = 5):
    """Ultimas execucoes de sync, com status e ERRO.

    Existia `POST /sync` para pedir e nada para ver o resultado: `sync_runs`
    guardava status, error_code e error_message e nada disso chegava na tela.
    O sintoma era o pior possivel — pedir sync, nao acontecer nada, e nao
    aparecer erro nenhum.

    Aceita workspace OU cliente porque linhas legadas (anteriores a 0087) tem
    `workspace_id` nulo, e ignora-las esconderia justamente o historico antigo.
    """
    return conn.execute(
        """
        select id, provider, status, error_code, error_message,
               records_processed, started_at, finished_at, summary
        from sync_runs
        where source = 'performance'
          and (workspace_id = %s or (workspace_id is null and client_id = %s))
        order by started_at desc
        limit %s
        """,
        (workspace_id, client_id, limit),
    ).fetchall()


def list_freshness(conn, client_id: UUID):
    return conn.execute(
        """
        select provider, status, last_synced_at, last_error_at, last_error_message
        from vw_performance_source_freshness
        where client_id = %s
        order by provider asc
        """,
        (client_id,),
    ).fetchall()


def get_ads_account_summary(conn, client_id: UUID, date_from: date, date_to: date):
    return conn.execute(
        """
        select
          coalesce(sum(impressions), 0)::bigint as impressions,
          coalesce(sum(clicks), 0)::bigint as clicks,
          coalesce(sum(cost_micros), 0)::bigint as cost_micros,
          coalesce(sum(conversions), 0)::numeric as conversions,
          coalesce(sum(conversion_value), 0)::numeric as conversion_value
        from ads_campaign_daily
        where client_id = %s and date between %s and %s
        """,
        (client_id, date_from, date_to),
    ).fetchone()


def list_ads_daily(conn, client_id: UUID, date_from: date, date_to: date):
    return conn.execute(
        """
        select
          date,
          coalesce(sum(impressions), 0)::bigint as impressions,
          coalesce(sum(clicks), 0)::bigint as clicks,
          coalesce(sum(cost_micros), 0)::bigint as cost_micros,
          coalesce(sum(conversions), 0)::numeric as conversions,
          coalesce(sum(conversion_value), 0)::numeric as conversion_value
        from ads_campaign_daily
        where client_id = %s and date between %s and %s
        group by date
        order by date asc
        """,
        (client_id, date_from, date_to),
    ).fetchall()


def list_ads_campaigns(conn, client_id: UUID, date_from: date, date_to: date, limit: int):
    return conn.execute(
        """
        select
          campaign_id,
          max(campaign_name) as campaign_name,
          max(campaign_status) as campaign_status,
          max(channel_type) as channel_type,
          max(budget_micros) as budget_micros,
          coalesce(sum(impressions), 0)::bigint as impressions,
          coalesce(sum(clicks), 0)::bigint as clicks,
          coalesce(sum(cost_micros), 0)::bigint as cost_micros,
          coalesce(sum(conversions), 0)::numeric as conversions,
          coalesce(sum(conversion_value), 0)::numeric as conversion_value,
          -- Impression share nao soma: e media ponderada pelas impressoes dos
          -- dias em que o Google reportou o dado (dias sem dado ficam de fora).
          (sum(search_impression_share * impressions)
             filter (where search_impression_share is not null)
           / nullif(sum(impressions) filter (where search_impression_share is not null), 0)
          )::numeric as search_impression_share
        from ads_campaign_daily
        where client_id = %s and date between %s and %s
        group by campaign_id
        order by cost_micros desc
        limit %s
        """,
        (client_id, date_from, date_to, limit),
    ).fetchall()


def list_ga4_acquisition(conn, client_id: UUID, date_from: date, date_to: date, limit: int):
    return conn.execute(
        """
        select
          source,
          medium,
          campaign,
          coalesce(sum(sessions), 0)::bigint as sessions,
          coalesce(sum(total_users), 0)::bigint as total_users,
          coalesce(sum(new_users), 0)::bigint as new_users,
          coalesce(sum(engaged_sessions), 0)::bigint as engaged_sessions,
          case
            when coalesce(sum(sessions), 0) > 0
              then coalesce(sum(engaged_sessions), 0)::numeric / sum(sessions)
            else 0
          end as engagement_rate,
          coalesce(sum(key_events), 0)::numeric as key_events
        from ga4_acquisition_daily
        where client_id = %s and date between %s and %s
        group by source, medium, campaign
        order by sessions desc
        limit %s
        """,
        (client_id, date_from, date_to, limit),
    ).fetchall()


def list_gsc_queries(conn, client_id: UUID, date_from: date, date_to: date, limit: int):
    return conn.execute(
        """
        select
          query,
          country,
          device,
          coalesce(sum(clicks), 0)::numeric as clicks,
          coalesce(sum(impressions), 0)::numeric as impressions,
          case
            when coalesce(sum(impressions), 0) > 0
              then coalesce(sum(clicks), 0)::numeric / sum(impressions)
            else 0
          end as ctr,
          case
            when coalesce(sum(impressions), 0) > 0
              then sum(position * impressions)::numeric / sum(impressions)
            else 0
          end as position
        from gsc_query_daily
        where client_id = %s and date between %s and %s
        group by query, country, device
        order by clicks desc, impressions desc
        limit %s
        """,
        (client_id, date_from, date_to, limit),
    ).fetchall()


def list_gtm_snapshots(conn, client_id: UUID, limit: int):
    return conn.execute(
        """
        select
          id,
          collected_at,
          account_id,
          container_id,
          workspace_id,
          gtm_workspace_id,
          published_version,
          jsonb_array_length(tags) as tags_count,
          jsonb_array_length(triggers) as triggers_count,
          jsonb_array_length(variables) as variables_count
        from gtm_audit_snapshots
        where client_id = %s
        order by collected_at desc
        limit %s
        """,
        (client_id, limit),
    ).fetchall()


def list_tracking_findings(conn, client_id: UUID, snapshot_ids: list[UUID]):
    if not snapshot_ids:
        return []
    return conn.execute(
        """
        select id, snapshot_id, code, title, description, severity, status, created_at
        from tracking_findings
        where client_id = %s and snapshot_id = any(%s)
        order by
          case severity
            when 'critical' then 0
            when 'high' then 1
            when 'medium' then 2
            when 'low' then 3
            else 4
          end,
          created_at desc
        """,
        (client_id, snapshot_ids),
    ).fetchall()


def list_insights(conn, client_id: UUID, date_from: date, date_to: date):
    return conn.execute(
        """
        select id, source, category, severity, title, description, recommendation,
               period_start, period_end, current_value, comparison_value, status, created_at
        from performance_insights
        where client_id = %s
          and status = 'active'
          and period_start <= %s
          and period_end >= %s
        order by
          case severity when 'critical' then 0 when 'warning' then 1 else 2 end,
          created_at desc
        limit 20
        """,
        (client_id, date_to, date_from),
    ).fetchall()


def count_active_connections(conn, client_id: UUID, provider: str) -> int:
    if provider == "all":
        row = conn.execute(
            """
            select count(*)::int as total
            from performance_connections
            where client_id = %s and status in ('active', 'error')
            """,
            (client_id,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            select count(*)::int as total
            from performance_connections
            where client_id = %s and provider = %s and status in ('active', 'error')
            """,
            (client_id, provider),
        ).fetchone()
    return row["total"]


def record_sync_request(
    conn,
    organization_id: UUID,
    client_id: UUID,
    provider: str,
    summary: dict[str, Any],
    date_from: date,
    date_to: date,
    records_processed: int = 0,
):
    return conn.execute(
        """
        insert into sync_runs (
          source, organization_id, client_id, provider, status, summary,
          date_from, date_to, records_processed
        )
        values ('performance', %s, %s, %s, 'queued', %s, %s, %s, %s)
        returning id, workspace_id, source, provider, status, summary, date_from, date_to,
                  records_processed, started_at, finished_at
        """,
        (
            organization_id,
            client_id,
            provider,
            Jsonb(summary),
            date_from,
            date_to,
            records_processed,
        ),
    ).fetchone()
