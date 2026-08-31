from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


def create_session(conn, actor_user_id: UUID, data: dict[str, Any]):
    return conn.execute(
        """
        insert into sales_copilot_sessions (
          workspace_id, opportunity_id, proposal_id, title, session_type, language, objective,
          participant_context, created_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning *
        """,
        (
            data.get("workspace_id"),
            data.get("opportunity_id"),
            data.get("proposal_id"),
            data["title"],
            data["session_type"],
            data["language"],
            data.get("objective"),
            data.get("participant_context"),
            actor_user_id,
        ),
    ).fetchone()


def get_session(conn, session_id: UUID, *, for_update: bool = False):
    suffix = " for update" if for_update else ""
    return conn.execute(
        f"select * from sales_copilot_sessions where id = %s{suffix}",
        (session_id,),
    ).fetchone()


def list_sessions(conn, limit: int = 50):
    return conn.execute(
        """
        select *
        from sales_copilot_sessions
        order by created_at desc
        limit %s
        """,
        (limit,),
    ).fetchall()


def list_events(conn, session_id: UUID):
    return conn.execute(
        """
        select *
        from sales_copilot_events
        where session_id = %s
        order by sequence, created_at
        """,
        (session_id,),
    ).fetchall()


def list_participants(conn, session_id: UUID):
    return conn.execute(
        """
        select *
        from sales_copilot_participants
        where session_id = %s
        order by created_at, display_name
        """,
        (session_id,),
    ).fetchall()


def add_participant(conn, session_id: UUID, actor_user_id: UUID | None, data: dict[str, Any]):
    return conn.execute(
        """
        insert into sales_copilot_participants (
          session_id, display_name, participant_group, organization_name, job_title,
          seniority, decision_role, email, external_speaker_id, context_notes, created_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (session_id, external_speaker_id)
        do update set
          display_name = excluded.display_name,
          participant_group = excluded.participant_group,
          organization_name = excluded.organization_name,
          job_title = excluded.job_title,
          seniority = excluded.seniority,
          decision_role = excluded.decision_role,
          email = excluded.email,
          context_notes = excluded.context_notes,
          updated_at = now()
        returning *
        """,
        (
            session_id,
            data["display_name"],
            data["participant_group"],
            data.get("organization_name"),
            data.get("job_title"),
            data["seniority"],
            data["decision_role"],
            data.get("email"),
            data.get("external_speaker_id"),
            data.get("context_notes"),
            actor_user_id,
        ),
    ).fetchone()


def configure_meeting(conn, session_id: UUID, data: dict[str, Any]):
    return conn.execute(
        """
        update sales_copilot_sessions
        set meeting_provider = %s,
            meeting_url = %s,
            external_meeting_id = %s,
            consent_status = %s,
            consent_recorded_at = case when %s = 'granted' then now() else consent_recorded_at end,
            retention_until = now() + make_interval(days => %s),
            realtime_status = case
              when %s <> 'manual' and %s = 'granted' then 'adapter_ready'
              else 'not_configured'
            end,
            updated_at = now()
        where id = %s
        returning *
        """,
        (
            data["meeting_provider"],
            data.get("meeting_url"),
            data.get("external_meeting_id"),
            data["consent_status"],
            data["consent_status"],
            data["retention_days"],
            data["meeting_provider"],
            data["consent_status"],
            session_id,
        ),
    ).fetchone()


def list_segments(conn, session_id: UUID, limit: int = 500):
    return conn.execute(
        """
        select *
        from sales_copilot_transcript_segments
        where session_id = %s
        order by sequence desc
        limit %s
        """,
        (session_id, limit),
    ).fetchall()[::-1]


def add_segment(conn, session_id: UUID, actor_user_id: UUID | None, data: dict[str, Any]):
    participant_id = data.get("participant_id")
    if not participant_id and data.get("external_speaker_id"):
        speaker = conn.execute(
            """
            select id from sales_copilot_participants
            where session_id = %s and external_speaker_id = %s
            """,
            (session_id, data["external_speaker_id"]),
        ).fetchone()
        if speaker:
            participant_id = speaker["id"]
        else:
            participant = add_participant(
                conn,
                session_id,
                actor_user_id,
                {
                    "display_name": data.get("speaker_label") or data["external_speaker_id"],
                    "participant_group": "unknown",
                    "organization_name": None,
                    "job_title": None,
                    "seniority": "unknown",
                    "decision_role": "unknown",
                    "email": None,
                    "external_speaker_id": data["external_speaker_id"],
                    "context_notes": "Criado automaticamente pela diarização; classificar antes da análise final.",
                },
            )
            participant_id = participant["id"]
    sequence = conn.execute(
        """
        select coalesce(max(sequence), 0) + 1 as next_sequence
        from sales_copilot_transcript_segments
        where session_id = %s
        """,
        (session_id,),
    ).fetchone()["next_sequence"]
    segment = conn.execute(
        """
        insert into sales_copilot_transcript_segments (
          session_id, participant_id, idempotency_key, source, external_speaker_id,
          speaker_label, start_ms, end_ms, content, confidence, is_final, sequence, created_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (session_id, idempotency_key) do update set
          participant_id = coalesce(excluded.participant_id, sales_copilot_transcript_segments.participant_id),
          speaker_label = coalesce(excluded.speaker_label, sales_copilot_transcript_segments.speaker_label),
          end_ms = excluded.end_ms,
          content = excluded.content,
          confidence = excluded.confidence,
          is_final = excluded.is_final
        returning *, (xmax = 0) as inserted
        """,
        (
            session_id,
            participant_id,
            data["idempotency_key"],
            data["source"],
            data.get("external_speaker_id"),
            data.get("speaker_label"),
            data["start_ms"],
            data.get("end_ms"),
            data["content"],
            data.get("confidence"),
            data["is_final"],
            sequence,
            actor_user_id,
        ),
    ).fetchone()
    if segment["is_final"] and segment["inserted"]:
        label = segment["speaker_label"]
        if participant_id:
            participant = conn.execute(
                "select display_name from sales_copilot_participants where id = %s and session_id = %s",
                (participant_id, session_id),
            ).fetchone()
            label = participant["display_name"] if participant else label
        rendered = f"{label}: {segment['content']}" if label else segment["content"]
        conn.execute(
            """
            update sales_copilot_sessions
            -- O cast ::text é obrigatório: dentro de concat_ws o Postgres não
            -- infere o tipo do parâmetro e derruba a query com
            -- IndeterminateDatatype (era 500 em toda ingestão de transcrição).
            set transcript = concat_ws(E'\n', nullif(transcript, ''), %s::text),
                status = case when status in ('draft', 'prepared') then 'active' else status end,
                realtime_status = case when meeting_provider <> 'manual' then 'live' else realtime_status end,
                started_at = coalesce(started_at, now()),
                updated_at = now()
            where id = %s
            """,
            (rendered, session_id),
        )
    return segment


def set_ingest_token_hash(conn, session_id: UUID, token_hash: str):
    return conn.execute(
        """
        update sales_copilot_sessions
        set ingest_token_hash = %s, updated_at = now()
        where id = %s
        returning *
        """,
        (token_hash, session_id),
    ).fetchone()


def list_suggestions(conn, session_id: UUID, limit: int = 100):
    return conn.execute(
        """
        select *
        from sales_copilot_live_suggestions
        where session_id = %s
        order by created_at desc
        limit %s
        """,
        (session_id, limit),
    ).fetchall()


def add_suggestion(conn, session_id: UUID, data: dict[str, Any]):
    return conn.execute(
        """
        insert into sales_copilot_live_suggestions (
          session_id, suggestion_type, title, content, rationale, confidence,
          source_refs, generation_mode
        ) values (%s, %s, %s, %s, %s, %s, %s, %s)
        returning *
        """,
        (
            session_id,
            data["suggestion_type"],
            data["title"],
            data["content"],
            data.get("rationale"),
            data.get("confidence"),
            Jsonb(data.get("source_refs", [])),
            data.get("generation_mode", "preview"),
        ),
    ).fetchone()


def list_actions(conn, session_id: UUID):
    return conn.execute(
        """
        select *
        from sales_copilot_actions
        where session_id = %s
        order by created_at, id
        """,
        (session_id,),
    ).fetchall()


def add_action(conn, session_id: UUID, actor_user_id: UUID, data: dict[str, Any]):
    return conn.execute(
        """
        insert into sales_copilot_actions (
          session_id, action_type, title, detail, owner_hint, due_at, source_refs,
          idempotency_key, created_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (session_id, idempotency_key)
        do update set title = excluded.title
        returning *
        """,
        (
            session_id,
            data["action_type"],
            data["title"],
            data.get("detail"),
            data.get("owner_hint"),
            data.get("due_at"),
            Jsonb(data.get("source_refs", [])),
            data.get("idempotency_key"),
            actor_user_id,
        ),
    ).fetchone()


def get_action(conn, action_id: UUID, *, for_update: bool = False):
    suffix = " for update" if for_update else ""
    return conn.execute(
        f"select * from sales_copilot_actions where id = %s{suffix}",
        (action_id,),
    ).fetchone()


def mark_action_materialized(
    conn,
    action_id: UUID,
    actor_user_id: UUID,
    idempotency_key: str,
    materialized_ref: dict[str, Any],
):
    return conn.execute(
        """
        update sales_copilot_actions
        set status = 'materialized',
            idempotency_key = coalesce(idempotency_key, %s),
            materialized_ref = %s,
            approved_by = %s,
            materialized_at = now(),
            updated_at = now()
        where id = %s
        returning *
        """,
        (idempotency_key, Jsonb(materialized_ref), actor_user_id, action_id),
    ).fetchone()


def prepare_session(
    conn,
    session_id: UUID,
    knowledge_snapshot: dict[str, Any],
    preparation_brief: dict[str, Any],
):
    return conn.execute(
        """
        update sales_copilot_sessions
        set knowledge_snapshot = %s,
            preparation_brief = %s,
            status = 'prepared',
            updated_at = now()
        where id = %s
        returning *
        """,
        (Jsonb(knowledge_snapshot), Jsonb(preparation_brief), session_id),
    ).fetchone()


def add_event(conn, session_id: UUID, actor_user_id: UUID, data: dict[str, Any]):
    sequence = conn.execute(
        """
        select coalesce(max(sequence), 0) + 1 as next_sequence
        from sales_copilot_events
        where session_id = %s
        """,
        (session_id,),
    ).fetchone()["next_sequence"]
    event = conn.execute(
        """
        insert into sales_copilot_events (
          session_id, event_type, content, recommendation, source_refs, sequence, created_by
        ) values (%s, %s, %s, %s, %s, %s, %s)
        returning *
        """,
        (
            session_id,
            data["event_type"],
            data["content"],
            data.get("recommendation"),
            Jsonb(data.get("source_refs", [])),
            sequence,
            actor_user_id,
        ),
    ).fetchone()
    if data["event_type"] == "transcript_chunk":
        conn.execute(
            """
            update sales_copilot_sessions
            -- O cast ::text é obrigatório: dentro de concat_ws o Postgres não
            -- infere o tipo do parâmetro e derruba a query com
            -- IndeterminateDatatype (era 500 em toda ingestão de transcrição).
            set transcript = concat_ws(E'\n', nullif(transcript, ''), %s::text),
                status = case when status in ('draft', 'prepared') then 'active' else status end,
                started_at = coalesce(started_at, now()),
                updated_at = now()
            where id = %s
            """,
            (data["content"], session_id),
        )
    return event


def complete_session(
    conn,
    session_id: UUID,
    duration_seconds: int,
    summary: str,
):
    return conn.execute(
        """
        update sales_copilot_sessions
        set status = 'completed',
            duration_seconds = %s,
            summary = %s,
            completed_at = now(),
            updated_at = now()
        where id = %s
        returning *
        """,
        (duration_seconds, summary, session_id),
    ).fetchone()


def link_opportunity(conn, session_id: UUID, opportunity_id: UUID):
    return conn.execute(
        """
        update sales_copilot_sessions
        set opportunity_id = %s, updated_at = now()
        where id = %s returning *
        """,
        (opportunity_id, session_id),
    ).fetchone()


def get_journey_snapshot(conn, session_id: UUID):
    return conn.execute(
        "select * from sales_journey_snapshots where session_id = %s",
        (session_id,),
    ).fetchone()


def upsert_journey_snapshot(conn, session_id: UUID, data: dict[str, Any]):
    return conn.execute(
        """
        insert into sales_journey_snapshots (
          session_id, workspace_id, opportunity_id, current_funnel_stage,
          funnel_map, journey_stages, scores, bottlenecks, recommended_actions,
          evidence_refs, generation_mode
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (session_id) do update set
          workspace_id = excluded.workspace_id,
          opportunity_id = excluded.opportunity_id,
          current_funnel_stage = excluded.current_funnel_stage,
          funnel_map = excluded.funnel_map,
          journey_stages = excluded.journey_stages,
          scores = excluded.scores,
          bottlenecks = excluded.bottlenecks,
          recommended_actions = excluded.recommended_actions,
          evidence_refs = excluded.evidence_refs,
          generation_mode = excluded.generation_mode,
          updated_at = now()
        returning *
        """,
        (
            session_id, data.get("workspace_id"), data.get("opportunity_id"),
            data["current_funnel_stage"], Jsonb(data["funnel_map"]), Jsonb(data["journey_stages"]),
            Jsonb(data["scores"]), Jsonb(data["bottlenecks"]), Jsonb(data["recommended_actions"]),
            Jsonb(data["evidence_refs"]), data["generation_mode"],
        ),
    ).fetchone()


def get_knowledge_context(
    conn, workspace_id: UUID | None, proposal_id: UUID | None, opportunity_id: UUID | None = None
):
    context: dict[str, Any] = {}
    if opportunity_id:
        opportunity = conn.execute(
            """
            select id, workspace_id, owner_user_id, source_platform, title, description, budget_text,
                   fit_score, fit_analysis, status, next_action_at, closed_at, updated_at
            from opportunity_radar where id = %s
            """,
            (opportunity_id,),
        ).fetchone()
        if opportunity:
            context["opportunity"] = dict(opportunity)
    if workspace_id:
        workspace = conn.execute(
            """
            select w.id, org.name as organization_name, profile.sector, profile.primary_offer,
              profile.target_audience, profile.business_details, profile.marketing_objectives,
              profile.challenges_opportunities, profile.tone_of_voice, profile.preferences_restrictions
            from workspaces w
            join organizations org on org.id = w.subject_organization_id
            left join workspace_client_profiles profile on profile.workspace_id = w.id
            where w.id = %s and w.status = 'active'
            """,
            (workspace_id,),
        ).fetchone()
        if workspace:
            context["client"] = dict(workspace)
    if proposal_id:
        proposal = conn.execute(
            """
            select id, workspace_id, title, client_name, status, executive_summary,
              problem_summary, selected_services, estimated_budget, payment_terms,
              content_markdown, claims_review_status
            from commercial_proposals
            where id = %s and archived_at is null
            """,
            (proposal_id,),
        ).fetchone()
        if proposal:
            context["proposal"] = dict(proposal)
            conversion = conn.execute(
                """
                select project_id, contract_id, plan_id
                from proposal_conversions
                where proposal_id = %s
                """,
                (proposal_id,),
            ).fetchone()
            if conversion:
                context["conversion"] = dict(conversion)
    if workspace_id:
        market_research = conn.execute(
            """
            select id, sector, geographic_scope, objective, status, report,
              generation_mode, updated_at
            from market_researches
            where workspace_id = %s and status = 'completed'
            order by updated_at desc
            limit 3
            """,
            (workspace_id,),
        ).fetchall()
        if market_research:
            context["market_research"] = [dict(row) for row in market_research]
    return context


def metrics(conn):
    rows = conn.execute(
        """
        select status, count(*)::int as count
        from sales_copilot_sessions
        group by status
        """
    ).fetchall()
    aggregate = conn.execute(
        """
        select count(*)::int as total_sessions,
          coalesce(sum(duration_seconds), 0)::int as total_duration_seconds,
          count(*) filter (where status = 'completed')::int as analyses_completed
        from sales_copilot_sessions
        """
    ).fetchone()
    return {
        **dict(aggregate),
        "sessions_by_status": {row["status"]: row["count"] for row in rows},
    }
