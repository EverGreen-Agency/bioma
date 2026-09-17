"""Sinais reais já disponíveis no Bioma para montar um rascunho de briefing.

Cada coletor devolve None/vazio quando a fonte não tem dado — o serviço reporta
essa ausência como ausência ("Instagram não conectado"), nunca preenche com
suposição. O briefing é rascunho de trabalho, não afirmação sobre o cliente.
"""

from datetime import date, timedelta
from typing import Any
from uuid import UUID


def profile(conn, workspace_id: UUID) -> dict[str, Any] | None:
    row = conn.execute(
        """
        select sector, primary_offer, initial_objective, website, business_details,
               target_audience, competitors, marketing_objectives, marketing_history,
               challenges_opportunities, resources_budget, tone_of_voice,
               preferences_restrictions
        from workspace_client_profiles
        where workspace_id = %s
        """,
        (workspace_id,),
    ).fetchone()
    return dict(row) if row else None


def paid_media(conn, client_id: UUID, days: int = 90) -> dict[str, Any] | None:
    since = date.today() - timedelta(days=days)
    row = conn.execute(
        """
        select coalesce(sum(cost_micros), 0) / 10000 as spend_cents,
               coalesce(sum(clicks), 0) as clicks,
               coalesce(sum(impressions), 0) as impressions,
               coalesce(sum(conversions), 0) as conversions,
               count(distinct campaign_id) as campaigns
        from ads_campaign_daily
        where client_id = %s and date >= %s
        """,
        (client_id, since),
    ).fetchone()
    if not row or not row["impressions"]:
        return None
    return dict(row)


def organic_social(conn, workspace_id: UUID, days: int = 90) -> dict[str, Any] | None:
    since = date.today() - timedelta(days=days)
    row = conn.execute(
        """
        select count(*) as posts,
               coalesce(avg(reach), 0) as avg_reach,
               coalesce(avg(likes + comments + shares + saved), 0) as avg_engagement,
               max(posted_at) as last_post_at
        from workspace_instagram_posts
        where workspace_id = %s and posted_at >= %s
        """,
        (workspace_id, since),
    ).fetchone()
    if not row or not row["posts"]:
        return None
    return dict(row)


def top_posts(conn, workspace_id: UUID, limit: int = 5) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select caption, media_type, reach, likes + comments + shares + saved as engagement
        from workspace_instagram_posts
        where workspace_id = %s and caption is not null
        order by (likes + comments + shares + saved) desc
        limit %s
        """,
        (workspace_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def search_presence(conn, client_id: UUID, days: int = 90) -> dict[str, Any] | None:
    since = date.today() - timedelta(days=days)
    row = conn.execute(
        """
        select coalesce(sum(clicks), 0) as clicks,
               coalesce(sum(impressions), 0) as impressions,
               count(distinct query) as queries
        from gsc_query_daily
        where client_id = %s and date >= %s
        """,
        (client_id, since),
    ).fetchone()
    if not row or not row["impressions"]:
        return None
    return dict(row)


def connections(conn, workspace_id: UUID) -> list[str]:
    rows = conn.execute(
        """
        select distinct provider
        from performance_connections
        where workspace_id = %s and status = 'active'
        order by provider
        """,
        (workspace_id,),
    ).fetchall()
    return [row["provider"] for row in rows]


def sector_research(conn, sector: str | None) -> dict[str, Any] | None:
    if not sector:
        return None
    row = conn.execute(
        """
        select id, sector, report
        from market_researches
        where status = 'completed' and report is not null
          and (sector ilike '%%' || %s || '%%' or %s ilike '%%' || sector || '%%')
        order by completed_at desc nulls last, created_at desc
        limit 1
        """,
        (sector, sector),
    ).fetchone()
    if not row:
        return None
    report = row["report"] or {}
    return {
        "research_id": str(row["id"]),
        "sector": row["sector"],
        "executive_summary": report.get("executive_summary"),
        "challenges": report.get("challenges", [])[:4],
        "growth_opportunities": report.get("growth_opportunities", [])[:4],
        "prospecting_playbook": report.get("prospecting_playbook"),
    }


def contracted_scope(conn, workspace_id: UUID) -> list[dict[str, Any]]:
    """Projetos ativos: o que foi contratado é o limite do que o briefing pode prometer."""
    rows = conn.execute(
        """
        select name, status, project_type, objective, start_at, due_at, cadence_days
        from projects
        where workspace_id = %s and status <> 'archived'
        order by created_at desc
        limit 10
        """,
        (workspace_id,),
    ).fetchall()
    return [dict(row) for row in rows]
