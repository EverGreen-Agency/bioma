from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def get_proposal(conn, proposal_id: UUID, *, for_update: bool = False):
    if for_update:
        return conn.execute(
            "select * from commercial_proposals where id = %s for update",
            (proposal_id,),
        ).fetchone()
    return conn.execute(
        """
        select cp.*, coalesce(o.source_platform, cp.target_niche, 'Outros') as source_platform
        from commercial_proposals cp
        left join opportunity_radar o on o.id = cp.opportunity_id
        where cp.id = %s
        """,
        (proposal_id,),
    ).fetchone()


def get_public_proposal(conn, public_token: str, *, for_update: bool = False):
    suffix = " for update" if for_update else ""
    return conn.execute(
        f"""
        select *
        from commercial_proposals
        where public_token = %s
          and public_expires_at > now()
          and archived_at is null{suffix}
        """,
        (public_token,),
    ).fetchone()


def list_revisions(conn, series_id: UUID):
    return conn.execute(
        """
        select *
        from commercial_proposals
        where series_id = %s
        order by version desc
        """,
        (series_id,),
    ).fetchall()


def list_events(conn, proposal_id: UUID):
    return conn.execute(
        """
        select *
        from proposal_events
        where proposal_id = %s
        order by created_at desc
        """,
        (proposal_id,),
    ).fetchall()


def list_deliveries(conn, proposal_id: UUID):
    return conn.execute(
        """
        select *
        from proposal_deliveries
        where proposal_id = %s
        order by created_at desc
        """,
        (proposal_id,),
    ).fetchall()


def find_conversion(conn, proposal_id: UUID):
    return conn.execute(
        "select * from proposal_conversions where proposal_id = %s",
        (proposal_id,),
    ).fetchone()


def find_conversion_by_idempotency_key(conn, idempotency_key: str):
    return conn.execute(
        "select * from proposal_conversions where idempotency_key = %s",
        (idempotency_key,),
    ).fetchone()


def record_event(
    conn,
    proposal_id: UUID,
    event_type: str,
    actor_user_id: UUID | None,
    payload: dict[str, Any] | None = None,
):
    return conn.execute(
        """
        insert into proposal_events (proposal_id, event_type, actor_user_id, payload)
        values (%s, %s, %s, %s)
        returning *
        """,
        (proposal_id, event_type, actor_user_id, Jsonb(payload or {})),
    ).fetchone()


def update_content(
    conn,
    proposal_id: UUID,
    content_markdown: str,
    claims: list[dict[str, Any]],
):
    return conn.execute(
        """
        update commercial_proposals
        set content_markdown = %s,
            claims = %s,
            claims_review_status = 'pending',
            updated_at = now()
        where id = %s
        returning *
        """,
        (content_markdown, Jsonb(claims), proposal_id),
    ).fetchone()


def review_claims(conn, proposal_id: UUID, review_status: str):
    return conn.execute(
        """
        update commercial_proposals
        set claims_review_status = %s, updated_at = now()
        where id = %s
        returning *
        """,
        (review_status, proposal_id),
    ).fetchone()


def transition_status(conn, proposal_id: UUID, next_status: str):
    timestamp_columns = {
        "approved": "approved_at",
        "sent": "sent_at",
        "negotiating": "negotiating_at",
        "won": "won_at",
        "lost": "lost_at",
    }
    timestamp_column = timestamp_columns.get(next_status)
    timestamp_sql = f", {timestamp_column} = coalesce({timestamp_column}, now())" if timestamp_column else ""
    return conn.execute(
        f"""
        update commercial_proposals
        set status = %s, updated_at = now(){timestamp_sql}
        where id = %s
        returning *
        """,
        (next_status, proposal_id),
    ).fetchone()


def create_revision(conn, proposal_id: UUID):
    source = get_proposal(conn, proposal_id, for_update=True)
    if not source:
        return None
    latest = conn.execute(
        """
        select version
        from commercial_proposals
        where series_id = %s
        order by version desc
        limit 1
        for update
        """,
        (source["series_id"],),
    ).fetchone()
    next_version = int(latest["version"]) + 1
    return conn.execute(
        """
        insert into commercial_proposals (
          opportunity_id, workspace_id, series_id, version, title, client_name, target_niche,
          executive_summary, scope_offer, scope_conversion, scope_demand, scope_items,
          attached_cases, win_loss_feedback, pricing_cents, delivery_days, status,
          generation_mode, created_by_user_id, proposal_type, contractor_name, team_members,
          delivery_modality, selected_services, special_requirements, estimated_budget,
          payment_terms, urgency, decision_maker, problem_summary, additional_context,
          intake_snapshot, content_markdown, content_sections, claims, claims_review_status
        )
        select
          opportunity_id, workspace_id, series_id, %s, title, client_name, target_niche,
          executive_summary, scope_offer, scope_conversion, scope_demand, scope_items,
          attached_cases, win_loss_feedback, pricing_cents, delivery_days, 'draft',
          generation_mode, created_by_user_id, proposal_type, contractor_name, team_members,
          delivery_modality, selected_services, special_requirements, estimated_budget,
          payment_terms, urgency, decision_maker, problem_summary, additional_context,
          intake_snapshot, content_markdown, content_sections, claims, claims_review_status
        from commercial_proposals
        where id = %s
        returning *
        """,
        (next_version, proposal_id),
    ).fetchone()


def archive_proposal(conn, proposal_id: UUID):
    return conn.execute(
        """
        update commercial_proposals
        set archived_at = coalesce(archived_at, now()), updated_at = now()
        where id = %s
        returning *
        """,
        (proposal_id,),
    ).fetchone()


def create_delivery(conn, proposal_id: UUID, actor_user_id: UUID, data: dict[str, Any]):
    delivery_status = "sent" if data.get("confirm_external_send") else "prepared"
    sent_at_sql = "now()" if delivery_status == "sent" else "null"
    row = conn.execute(
        f"""
        insert into proposal_deliveries (
          proposal_id, channel, recipient_name, recipient_email, provider, external_id,
          status, metadata, sent_at, created_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, {sent_at_sql}, %s)
        returning *
        """,
        (
            proposal_id,
            data["channel"],
            data.get("recipient_name"),
            data.get("recipient_email"),
            data.get("provider"),
            data.get("external_id"),
            delivery_status,
            Jsonb({"external_send_confirmed": bool(data.get("confirm_external_send"))}),
            actor_user_id,
        ),
    ).fetchone()
    conn.execute(
        """
        update commercial_proposals
        set acceptance_status = case
              when %s = 'signature_adapter' then 'pending'
              else acceptance_status
            end,
            sent_at = case when %s then coalesce(sent_at, now()) else sent_at end,
            status = case when %s and status in ('draft', 'approved') then 'sent' else status end,
            updated_at = now()
        where id = %s
        """,
        (
            data["channel"],
            bool(data.get("confirm_external_send")),
            bool(data.get("confirm_external_send")),
            proposal_id,
        ),
    )
    return row


def mark_viewed(conn, proposal_id: UUID):
    return conn.execute(
        """
        update commercial_proposals
        set viewed_at = coalesce(viewed_at, now())
        where id = %s
        returning *
        """,
        (proposal_id,),
    ).fetchone()


def record_acceptance(
    conn,
    proposal_id: UUID,
    *,
    accepted: bool,
    signer_name: str,
    signer_email: str,
):
    acceptance_status = "accepted" if accepted else "rejected"
    return conn.execute(
        """
        update commercial_proposals
        set acceptance_status = %s,
            accepted_at = case when %s then now() else null end,
            accepted_by_name = %s,
            accepted_by_email = %s,
            status = case when %s then 'won' else status end,
            won_at = case when %s then coalesce(won_at, now()) else won_at end,
            updated_at = now()
        where id = %s
        returning *
        """,
        (
            acceptance_status,
            accepted,
            signer_name,
            signer_email,
            accepted,
            accepted,
            proposal_id,
        ),
    ).fetchone()


def insert_conversion(
    conn,
    proposal_id: UUID,
    idempotency_key: str,
    project_id: UUID,
    contract_id: UUID,
    actor_user_id: UUID,
):
    return conn.execute(
        """
        insert into proposal_conversions (
          proposal_id, idempotency_key, project_id, contract_id, created_by
        ) values (%s, %s, %s, %s, %s)
        on conflict (proposal_id) do update set proposal_id = excluded.proposal_id
        returning *
        """,
        (proposal_id, idempotency_key, project_id, contract_id, actor_user_id),
    ).fetchone()


def attach_conversion_plan(conn, conversion_id: UUID, plan_id: UUID):
    return conn.execute(
        """
        update proposal_conversions
        set plan_id = coalesce(plan_id, %s)
        where id = %s
        returning *
        """,
        (plan_id, conversion_id),
    ).fetchone()


def cohort_analytics(conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            with cohorts as (
              select
                to_char(date_trunc('month', created_at), 'YYYY-MM') as month,
                count(*)::int as created,
                count(*) filter (where sent_at is not null)::int as sent,
                count(*) filter (where status = 'won')::int as won,
                count(*) filter (where status = 'lost')::int as lost,
                avg(extract(epoch from (coalesce(won_at, lost_at) - created_at)) / 86400.0)
                  filter (where status in ('won', 'lost')) as average_days_to_close
              from commercial_proposals
              where archived_at is null
              group by date_trunc('month', created_at)
              order by date_trunc('month', created_at) desc
            )
            select month, created, sent, won, lost,
              case when won + lost = 0 then 0
                   else round((won::numeric / (won + lost)) * 100, 2)
              end as win_rate_percentage,
              round(average_days_to_close::numeric, 2) as average_days_to_close
            from cohorts
            """
        )
        cohorts = list(cur.fetchall())
        cur.execute(
            """
            select
              percentile_cont(0.5) within group (
                order by extract(epoch from (sent_at - created_at)) / 86400.0
              ) filter (where sent_at is not null) as median_days_to_first_send,
              percentile_cont(0.5) within group (
                order by extract(epoch from (coalesce(won_at, lost_at) - created_at)) / 86400.0
              ) filter (where status in ('won', 'lost')) as median_days_to_close
            from commercial_proposals
            where archived_at is null
            """
        )
        medians = dict(cur.fetchone())
    return cohorts, medians
