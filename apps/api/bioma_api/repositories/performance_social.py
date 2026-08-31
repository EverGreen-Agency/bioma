from datetime import date
from uuid import UUID

from psycopg.types.json import Jsonb


def upsert_meta_ads_daily(conn, workspace_id: UUID, client_id: UUID | None, metrics: list[dict]):
    sql = """
        insert into workspace_meta_ads_daily_metrics (
          workspace_id, client_id, date, account_id, account_name,
          campaign_id, campaign_name, impressions, clicks, spend_cents,
          conversions, leads, revenue_cents
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (workspace_id, campaign_id, date) do update set
          impressions = excluded.impressions,
          clicks = excluded.clicks,
          spend_cents = excluded.spend_cents,
          conversions = excluded.conversions,
          leads = excluded.leads,
          revenue_cents = excluded.revenue_cents
    """
    for m in metrics:
        conn.execute(
            sql,
            (
                workspace_id,
                client_id,
                m["date"],
                m.get("account_id"),
                m.get("account_name"),
                m["campaign_id"],
                m["campaign_name"],
                m.get("impressions", 0),
                m.get("clicks", 0),
                m.get("spend_cents", 0),
                m.get("conversions", 0),
                m.get("leads", 0),
                m.get("revenue_cents", 0),
            ),
        )


def list_meta_ads_daily(conn, workspace_id: UUID, limit: int = 30):
    return conn.execute(
        """
        select id, workspace_id, client_id, date, account_id, account_name,
          campaign_id, campaign_name, impressions, clicks, spend_cents,
          conversions, leads, revenue_cents, created_at
        from workspace_meta_ads_daily_metrics
        where workspace_id = %s
        order by date desc
        limit %s
        """,
        (workspace_id, limit),
    ).fetchall()


def upsert_linkedin_ads_daily(conn, workspace_id: UUID, client_id: UUID | None, metrics: list[dict]):
    sql = """
        insert into workspace_linkedin_ads_daily_metrics (
          workspace_id, client_id, date, account_id, account_name,
          campaign_id, campaign_name, impressions, clicks, spend_cents,
          conversions, leads, revenue_cents
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (workspace_id, campaign_id, date) do update set
          impressions = excluded.impressions,
          clicks = excluded.clicks,
          spend_cents = excluded.spend_cents,
          conversions = excluded.conversions,
          leads = excluded.leads,
          revenue_cents = excluded.revenue_cents
    """
    for m in metrics:
        conn.execute(
            sql,
            (
                workspace_id,
                client_id,
                m["date"],
                m.get("account_id"),
                m.get("account_name"),
                m["campaign_id"],
                m["campaign_name"],
                m.get("impressions", 0),
                m.get("clicks", 0),
                m.get("spend_cents", 0),
                m.get("conversions", 0),
                m.get("leads", 0),
                m.get("revenue_cents", 0),
            ),
        )


def list_linkedin_ads_daily(conn, workspace_id: UUID, limit: int = 30):
    return conn.execute(
        """
        select id, workspace_id, client_id, date, account_id, account_name,
          campaign_id, campaign_name, impressions, clicks, spend_cents,
          conversions, leads, revenue_cents, created_at
        from workspace_linkedin_ads_daily_metrics
        where workspace_id = %s
        order by date desc
        limit %s
        """,
        (workspace_id, limit),
    ).fetchall()


def get_multichannel_totals(conn, workspace_id: UUID):
    meta = conn.execute(
        """
        select coalesce(sum(impressions), 0) as impressions,
               coalesce(sum(clicks), 0) as clicks,
               coalesce(sum(spend_cents), 0) as spend_cents,
               coalesce(sum(conversions), 0) as conversions,
               coalesce(sum(leads), 0) as leads
        from workspace_meta_ads_daily_metrics
        where workspace_id = %s
        """,
        (workspace_id,),
    ).fetchone()

    linkedin = conn.execute(
        """
        select coalesce(sum(impressions), 0) as impressions,
               coalesce(sum(clicks), 0) as clicks,
               coalesce(sum(spend_cents), 0) as spend_cents,
               coalesce(sum(conversions), 0) as conversions,
               coalesce(sum(leads), 0) as leads
        from workspace_linkedin_ads_daily_metrics
        where workspace_id = %s
        """,
        (workspace_id,),
    ).fetchone()

    return {"meta": meta, "linkedin": linkedin}
