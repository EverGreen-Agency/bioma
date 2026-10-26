from uuid import UUID

from psycopg.types.json import Jsonb


def get_config_public(conn, organization_id: UUID):
    return conn.execute(
        "select subdomain, updated_at from kommo_integrations where organization_id = %s",
        (organization_id,),
    ).fetchone()


def get_integration(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, organization_id, client_id, client_secret, access_token, refresh_token, subdomain
        from kommo_integrations
        where organization_id = %s
        """,
        (organization_id,),
    ).fetchone()


def list_integrations(conn):
    return conn.execute(
        """
        select id, organization_id, client_id, client_secret, access_token, refresh_token, subdomain
        from kommo_integrations
        """
    ).fetchall()


def upsert_integration(
    conn,
    organization_id: UUID,
    client_id: str,
    client_secret: str,
    access_token: str,
    subdomain: str,
) -> None:
    conn.execute(
        """
        insert into kommo_integrations (organization_id, client_id, client_secret, access_token, subdomain)
        values (%s, %s, %s, %s, %s)
        on conflict (organization_id) do update set
            client_id = excluded.client_id,
            client_secret = excluded.client_secret,
            access_token = excluded.access_token,
            subdomain = excluded.subdomain,
            updated_at = now()
        """,
        (organization_id, client_id, client_secret, access_token, subdomain),
    )


def update_tokens(conn, organization_id: UUID, access_token: str, refresh_token: str | None) -> None:
    conn.execute(
        """
        update kommo_integrations
        set access_token = %s,
            refresh_token = coalesce(%s, refresh_token),
            updated_at = now()
        where organization_id = %s
        """,
        (access_token, refresh_token, organization_id),
    )


def latest_metrics(conn, organization_id: UUID):
    return conn.execute(
        """
        select pipeline_id, pipeline_name, snapshot_date, total_leads, won_leads,
               lost_leads, active_leads, total_value, won_value
        from kommo_metrics_snapshots
        where organization_id = %s
          and snapshot_date = (
              select max(snapshot_date)
              from kommo_metrics_snapshots
              where organization_id = %s
          )
        order by pipeline_name asc
        """,
        (organization_id, organization_id),
    ).fetchall()


def upsert_crm_snapshot(
    conn,
    organization_id: UUID,
    subdomain: str,
    pipelines: list,
    leads: list,
    fetched_by: UUID,
) -> None:
    conn.execute(
        """
        insert into kommo_crm_snapshots (organization_id, subdomain, leads_count, pipelines, leads, fetched_by)
        values (%s, %s, %s, %s, %s, %s)
        on conflict (organization_id) do update set
            subdomain = excluded.subdomain,
            leads_count = excluded.leads_count,
            pipelines = excluded.pipelines,
            leads = excluded.leads,
            fetched_by = excluded.fetched_by,
            fetched_at = now()
        """,
        (organization_id, subdomain, len(leads), Jsonb(pipelines), Jsonb(leads), fetched_by),
    )


def get_crm_snapshot(conn, organization_id: UUID):
    return conn.execute(
        """
        select subdomain, leads_count, pipelines, leads, fetched_at
        from kommo_crm_snapshots
        where organization_id = %s
        """,
        (organization_id,),
    ).fetchone()


def insert_dedup_run(conn, organization_id: UUID, requested_by: UUID, subdomain: str, report: dict):
    return conn.execute(
        """
        insert into kommo_dedup_runs
          (organization_id, requested_by, subdomain, contacts_scanned, clusters_count,
           duplicates_count, leads_to_reassign, report)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        returning id, created_at
        """,
        (
            organization_id,
            requested_by,
            subdomain,
            report.get("total_contacts_scanned", 0),
            report.get("duplicate_clusters_count", 0),
            report.get("total_duplicates_detected", 0),
            report.get("total_leads_to_reassign", 0),
            Jsonb(report),
        ),
    ).fetchone()


def list_dedup_runs(conn, organization_id: UUID, limit: int = 20):
    return conn.execute(
        """
        select run.id, run.subdomain, run.contacts_scanned, run.clusters_count, run.duplicates_count,
               run.leads_to_reassign, run.created_at, requester.display_name as requested_by_name
        from kommo_dedup_runs run
        left join users requester on requester.id = run.requested_by
        where run.organization_id = %s
        order by run.created_at desc
        limit %s
        """,
        (organization_id, limit),
    ).fetchall()


def get_dedup_run(conn, organization_id: UUID, run_id: UUID):
    return conn.execute(
        """
        select id, subdomain, contacts_scanned, clusters_count, duplicates_count,
               leads_to_reassign, report, created_at
        from kommo_dedup_runs
        where organization_id = %s and id = %s
        """,
        (organization_id, run_id),
    ).fetchone()


# --- Portal público por slug (painel v2 e portal EG) ---------------------------


def find_organization_by_slug(conn, slug: str):
    return conn.execute("select id, name, slug from organizations where slug = %s", (slug,)).fetchone()


def update_dedup_run_report(conn, run_id: UUID, report: dict, clusters_applied: int) -> None:
    conn.execute(
        "update kommo_dedup_runs set report = %s, clusters_applied = %s where id = %s",
        (Jsonb(report), clusters_applied, run_id),
    )


def latest_dedup_run(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, subdomain, contacts_scanned, clusters_count, duplicates_count,
               leads_to_reassign, clusters_applied, created_at
        from kommo_dedup_runs
        where organization_id = %s
        order by created_at desc
        limit 1
        """,
        (organization_id,),
    ).fetchone()


def upsert_lead_classification(
    conn,
    organization_id: UUID,
    lead_id: int,
    status: str,
    engine: str,
    messages_count: int,
    fields: dict,
    fields_written: int,
    error: str | None,
    trigger: str,
) -> None:
    conn.execute(
        """
        insert into kommo_lead_classifications
          (organization_id, lead_id, status, engine, messages_count, fields, fields_written, error, trigger)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (organization_id, lead_id) do update set
            status = excluded.status,
            engine = excluded.engine,
            messages_count = excluded.messages_count,
            fields = excluded.fields,
            fields_written = kommo_lead_classifications.fields_written + excluded.fields_written,
            error = excluded.error,
            trigger = excluded.trigger,
            classified_at = now()
        """,
        (organization_id, lead_id, status, engine, messages_count, Jsonb(fields), fields_written, error, trigger),
    )


def classified_lead_ids(conn, organization_id: UUID, include_simulated: bool) -> set[int]:
    """Leads que já saíram da fila. Um lead só simulado continua na fila de gravação."""
    rows = conn.execute(
        """
        select lead_id from kommo_lead_classifications
        where organization_id = %s and (%s or trigger <> 'simulacao')
        """,
        (organization_id, include_simulated),
    ).fetchall()
    return {row["lead_id"] for row in rows}


def get_lead_classification(conn, organization_id: UUID, lead_id: int):
    return conn.execute(
        "select classified_at, status, fields_written from kommo_lead_classifications where organization_id = %s and lead_id = %s",
        (organization_id, lead_id),
    ).fetchone()


def get_lead_classification_detail(conn, organization_id: UUID, lead_id: int):
    return conn.execute(
        """
        select lead_id, status, engine, messages_count, fields, fields_written, error, trigger, classified_at
        from kommo_lead_classifications
        where organization_id = %s and lead_id = %s
        """,
        (organization_id, lead_id),
    ).fetchone()


def update_lead_classification_applied(
    conn,
    organization_id: UUID,
    lead_id: int,
    fields: dict,
    fields_written: int,
) -> None:
    conn.execute(
        """
        update kommo_lead_classifications
        set status = 'gravado',
            fields = %s,
            fields_written = %s,
            classified_at = now()
        where organization_id = %s and lead_id = %s
        """,
        (Jsonb(fields), fields_written, organization_id, lead_id),
    )


def list_pending_suggested_lead_ids(conn, organization_id: UUID, limit: int) -> list[int]:
    rows = conn.execute(
        """
        select lead_id
        from kommo_lead_classifications
        where organization_id = %s
          and status in ('sugerido', 'classificado')
          and fields_written = 0
          and fields <> '{}'::jsonb
        order by classified_at desc
        limit %s
        """,
        (organization_id, limit),
    ).fetchall()
    return [r["lead_id"] for r in rows]


def list_written_lead_ids(conn, organization_id: UUID, limit: int) -> list[int]:
    rows = conn.execute(
        """
        select lead_id
        from kommo_lead_classifications
        where organization_id = %s
          and (status = 'gravado' or fields_written > 0)
        order by classified_at desc
        limit %s
        """,
        (organization_id, limit),
    ).fetchall()
    return [r["lead_id"] for r in rows]


def update_lead_classification_cleared(conn, organization_id: UUID, lead_id: int) -> None:
    conn.execute(
        """
        update kommo_lead_classifications
        set status = 'limpo',
            fields_written = 0,
            classified_at = now()
        where organization_id = %s and lead_id = %s
        """,
        (organization_id, lead_id),
    )


def classification_summary(conn, organization_id: UUID):
    return conn.execute(
        """
        select count(*) as total,
               count(*) filter (where trigger = 'simulacao') as simulated,
               count(*) filter (where status in ('classificado', 'sugerido', 'gravado')) as classified,
               count(*) filter (where status in ('sugerido', 'classificado') and fields_written = 0) as suggested,
               count(*) filter (where status = 'gravado' or fields_written > 0) as written_leads,
               count(*) filter (where status = 'aguardando_cliente') as waiting_customer,
               count(*) filter (where status = 'sem_conversa') as without_conversation,
               count(*) filter (where status = 'erro') as errors,
               coalesce(sum(fields_written), 0) as fields_written,
               max(classified_at) as last_at
        from kommo_lead_classifications
        where organization_id = %s
        """,
        (organization_id,),
    ).fetchone()


def list_lead_classifications(conn, organization_id: UUID, limit: int, offset: int):
    return conn.execute(
        """
        select lead_id, status, engine, messages_count, fields, fields_written, error, trigger, classified_at
        from kommo_lead_classifications
        where organization_id = %s
        order by classified_at desc
        limit %s offset %s
        """,
        (organization_id, limit, offset),
    ).fetchall()


def clear_lead_classifications(conn, organization_id: UUID) -> int:
    cursor = conn.execute(
        "delete from kommo_lead_classifications where organization_id = %s",
        (organization_id,),
    )
    return getattr(cursor, "rowcount", 0)



def get_webhook(conn, organization_id: UUID):
    return conn.execute(
        """
        select secret, kommo_webhook_id, destination, events, last_event_at, events_received, created_at
        from kommo_webhooks
        where organization_id = %s
        """,
        (organization_id,),
    ).fetchone()


def upsert_webhook(conn, organization_id: UUID, secret: str, kommo_webhook_id: int | None, destination: str, events: list[str]) -> None:
    conn.execute(
        """
        insert into kommo_webhooks (organization_id, secret, kommo_webhook_id, destination, events)
        values (%s, %s, %s, %s, %s)
        on conflict (organization_id) do update set
            secret = excluded.secret,
            kommo_webhook_id = excluded.kommo_webhook_id,
            destination = excluded.destination,
            events = excluded.events,
            created_at = now()
        """,
        (organization_id, secret, kommo_webhook_id, destination, events),
    )


def touch_webhook(conn, organization_id: UUID) -> None:
    conn.execute(
        "update kommo_webhooks set last_event_at = now(), events_received = events_received + 1 where organization_id = %s",
        (organization_id,),
    )
