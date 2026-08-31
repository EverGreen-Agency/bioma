from uuid import UUID


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
