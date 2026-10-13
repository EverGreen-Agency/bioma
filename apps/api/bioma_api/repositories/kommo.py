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
