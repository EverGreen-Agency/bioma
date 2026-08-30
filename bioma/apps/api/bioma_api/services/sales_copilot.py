from __future__ import annotations

import hashlib
import secrets
from hmac import compare_digest
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import projects as projects_repo
from bioma_api.repositories import proposal_lifecycle as lifecycle_repo
from bioma_api.repositories import proposals as proposals_repo
from bioma_api.repositories import sales_copilot as copilot_repo
from bioma_api.repositories import tasks as tasks_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.sales_copilot import (
    FathomImportRequest,
    FathomImportResult,
    FathomMeeting,
    RealtimeAdapterStatus,
    SalesCopilotAction,
    SalesCopilotActionCreate,
    SalesCopilotActionMaterialize,
    SalesCopilotCompleteRequest,
    SalesCopilotEvent,
    SalesCopilotEventCreate,
    SalesCopilotIngestionAck,
    SalesCopilotIngestionCredential,
    SalesJourneySnapshot,
    SalesCopilotLiveAnalyzeRequest,
    SalesCopilotLiveSuggestion,
    SalesCopilotMeetingConfigure,
    SalesCopilotMetrics,
    SalesCopilotParticipant,
    SalesCopilotParticipantCreate,
    SalesCopilotSession,
    SalesCopilotSessionCreate,
    SalesCopilotTranscriptBatch,
    SalesCopilotTranscriptSegment,
)
from bioma_api.worker_bridge import (
    analyze_sales_live_window_safe,
    execute_squad_pipeline_safe,
    sales_live_suggestion_type,
    get_fathom_transcript_safe,
    list_fathom_meetings_safe,
)


def list_sessions(user: CurrentUserResponse) -> list[SalesCopilotSession]:
    require_platform_admin(user)
    with connect() as conn:
        return [_session(conn, row) for row in copilot_repo.list_sessions(conn)]


def get_session(session_id: UUID, user: CurrentUserResponse) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        return _session(conn, _find(conn, session_id))


def create_session(
    payload: SalesCopilotSessionCreate,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        context = copilot_repo.get_knowledge_context(
            conn, payload.workspace_id, payload.proposal_id, payload.opportunity_id
        )
        _validate_context(payload.workspace_id, payload.proposal_id, context, payload.opportunity_id)
        return _session(conn, copilot_repo.create_session(conn, user.id, payload.model_dump()))


def prepare_session(session_id: UUID, user: CurrentUserResponse) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        row = _find(conn, session_id, for_update=True)
        context = copilot_repo.get_knowledge_context(
            conn, row["workspace_id"], row["proposal_id"], row.get("opportunity_id")
        )
        participants = jsonable_encoder(
            [dict(item) for item in copilot_repo.list_participants(conn, session_id)]
        )
        context = jsonable_encoder(context)
    ai_result = execute_squad_pipeline_safe(
        pilar="conversao",
        squad_key="sales_copilot",
        input_context={
            "objective": row["objective"] or row["title"],
            "project_title": row["title"],
            "project_description": row["participant_context"] or "",
            "participants": participants,
            "knowledge_context": context,
            "source": "sales_copilot_preparation",
        },
        requested_by_user_id=str(user.id),
    )
    output = ai_result["output_data"]
    brief = {
        "generation_mode": ai_result["generation_mode"],
        "meeting_objective": row["objective"] or row["title"],
        "opening": output.get("script_fechamento") or "Validar contexto, dor, impacto e próximo passo.",
        "objection_map": output.get("objecoes") or output.get("objection_map") or [],
        "recommended_questions": output.get("perguntas") or [
            "Qual impacto do problema hoje?",
            "Quem participa da decisão?",
            "Qual prazo real para resolver?",
        ],
        "participant_roles": [
            {
                "name": item["display_name"],
                "group": item["participant_group"],
                "job_title": item["job_title"],
                "decision_role": item["decision_role"],
            }
            for item in participants
        ],
        "knowledge_used": sorted(context),
    }
    with connect() as conn:
        _find(conn, session_id, for_update=True)
        return _session(conn, copilot_repo.prepare_session(conn, session_id, context, brief))


def add_event(
    session_id: UUID,
    payload: SalesCopilotEventCreate,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        session = _find_open_session(conn, session_id)
        copilot_repo.add_event(conn, session["id"], user.id, payload.model_dump(mode="json"))
        return _session(conn, _find(conn, session_id))


def configure_meeting(
    session_id: UUID,
    payload: SalesCopilotMeetingConfigure,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    if payload.meeting_provider != "manual" and not payload.meeting_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe o link da reunião para Meet ou Teams.",
        )
    with connect() as conn:
        _find_open_session(conn, session_id)
        copilot_repo.configure_meeting(
            conn,
            session_id,
            {
                **payload.model_dump(mode="json"),
                "consent_status": "granted" if payload.consent_granted else "pending",
            },
        )
        return _session(conn, _find(conn, session_id))


def add_participant(
    session_id: UUID,
    payload: SalesCopilotParticipantCreate,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        _find_open_session(conn, session_id)
        copilot_repo.add_participant(conn, session_id, user.id, payload.model_dump(mode="json"))
        return _session(conn, _find(conn, session_id))


def ingest_transcript(
    session_id: UUID,
    payload: SalesCopilotTranscriptBatch,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        session = _find_open_session(conn, session_id)
        non_manual = any(segment.source not in {"manual", "upload"} for segment in payload.segments)
        if non_manual and session["consent_status"] != "granted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A ingestão do Meet/Teams exige consentimento registrado.",
            )
        participant_ids = {participant["id"] for participant in copilot_repo.list_participants(conn, session_id)}
        for segment in payload.segments:
            if segment.participant_id and segment.participant_id not in participant_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="O participante informado não pertence a esta sessão.",
                )
            if segment.end_ms is not None and segment.end_ms < segment.start_ms:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="O fim do segmento não pode ser anterior ao início.",
                )
            copilot_repo.add_segment(conn, session_id, user.id, segment.model_dump(mode="json"))
        result = _session(conn, _find(conn, session_id))
    if payload.analyze_after_ingest and len(result.segments) >= 3:
        return analyze_live(session_id, SalesCopilotLiveAnalyzeRequest(), user)
    return result


def issue_ingestion_credential(
    session_id: UUID,
    user: CurrentUserResponse,
) -> SalesCopilotIngestionCredential:
    require_platform_admin(user)
    token = secrets.token_urlsafe(36)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with connect() as conn:
        session = _find_open_session(conn, session_id)
        if session["consent_status"] != "granted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registre o consentimento antes de habilitar um adaptador externo.",
            )
        copilot_repo.set_ingest_token_hash(conn, session_id, token_hash)
        copilot_repo.add_event(
            conn,
            session_id,
            user.id,
            {
                "event_type": "note",
                "content": "Credencial de ingestão rotacionada.",
                "recommendation": "O token é exibido uma única vez e deve ficar no secret store do adaptador.",
                "source_refs": [],
            },
        )
    return SalesCopilotIngestionCredential(
        session_id=session_id,
        ingest_token=token,
        endpoint_path=f"/backoffice/sales-copilot/ingest/{session_id}",
    )


def ingest_external_transcript(
    session_id: UUID,
    payload: SalesCopilotTranscriptBatch,
    ingest_token: str,
) -> SalesCopilotIngestionAck:
    token_hash = hashlib.sha256(ingest_token.encode("utf-8")).hexdigest()
    with connect() as conn:
        session = _find_open_session(conn, session_id)
        expected_hash = session.get("ingest_token_hash")
        if not expected_hash or not compare_digest(expected_hash, token_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial de ingestão inválida.")
        if session["consent_status"] != "granted":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Consentimento ausente ou revogado.")
        for segment in payload.segments:
            if segment.source not in {"google_meet", "microsoft_teams", "provider_webhook"}:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="O adaptador externo só aceita segmentos de Meet, Teams ou webhook.",
                )
            copilot_repo.add_segment(conn, session_id, None, segment.model_dump(mode="json"))
    return SalesCopilotIngestionAck(session_id=session_id, accepted_segments=len(payload.segments))


def analyze_live(
    session_id: UUID,
    payload: SalesCopilotLiveAnalyzeRequest,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        row = _find(conn, session_id)
        segments = copilot_repo.list_segments(conn, session_id, payload.window_segments)
        participants = copilot_repo.list_participants(conn, session_id)
        context = row["knowledge_snapshot"] or copilot_repo.get_knowledge_context(
            conn, row["workspace_id"], row["proposal_id"], row.get("opportunity_id"),
        )
        participants = jsonable_encoder([dict(item) for item in participants])
        context = jsonable_encoder(context)
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Inclua segmentos da conversa antes de solicitar uma sugestão.",
        )
    transcript_window = "\n".join(
        f"{segment['speaker_label'] or 'Falante'}: {segment['content']}" for segment in segments
    )
    # Caminho dedicado (não o squad genérico): schema fechado, janela recente e
    # um round-trip. O tipo da sugestão vem da classificação do modelo, não de
    # busca por palavra — "não ficou caro" deixou de virar objeção de preço.
    try:
        ai_result = analyze_sales_live_window_safe(
            {
                "objective": payload.focus or row["objective"] or "Ajudar a conduzir a reunião",
                "title": row["title"],
                "transcript_window": transcript_window,
                "participants": participants,
                "knowledge_context": context,
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A análise ao vivo falhou. Tente novamente em alguns segundos.",
        ) from exc

    output = ai_result["output"]
    suggestion_type = sales_live_suggestion_type(output.get("moment", ""))
    recommendation = output.get("suggested_line") or ""
    rationale_parts = [output.get("rationale") or ""]
    if output.get("signals"):
        rationale_parts.append("Sinais: " + " · ".join(output["signals"]))
    if output.get("next_question"):
        rationale_parts.append(f"Pergunta que destrava: {output['next_question']}")
    if output.get("risk"):
        rationale_parts.append(f"Risco agora: {output['risk']}")
    with connect() as conn:
        _find(conn, session_id, for_update=True)
        copilot_repo.add_suggestion(
            conn,
            session_id,
            {
                "suggestion_type": suggestion_type,
                "title": f"Momento: {output.get('moment', 'indefinido')}",
                "content": str(recommendation),
                "rationale": " | ".join(part for part in rationale_parts if part),
                "confidence": None,
                "source_refs": [
                    {"kind": "transcript_segment", "id": str(segment["id"])}
                    for segment in segments
                ],
                "generation_mode": ai_result["generation_mode"],
            },
        )
        return _session(conn, _find(conn, session_id))


def add_action(
    session_id: UUID,
    payload: SalesCopilotActionCreate,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        _find(conn, session_id)
        copilot_repo.add_action(conn, session_id, user.id, payload.model_dump(mode="json"))
        return _session(conn, _find(conn, session_id))


def materialize_action(
    action_id: UUID,
    payload: SalesCopilotActionMaterialize,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Confirmação HITL obrigatória.")
    with connect() as conn:
        action = copilot_repo.get_action(conn, action_id, for_update=True)
        if not action:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compromisso não encontrado.")
        session = _find(conn, action["session_id"], for_update=True)
        if action["status"] == "materialized":
            return _session(conn, session)
        if action["idempotency_key"] and action["idempotency_key"] != payload.idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O compromisso já foi reservado com outra chave.",
            )
        materialized_ref = _materialize_action_in_transaction(conn, session, action, user)
        copilot_repo.mark_action_materialized(
            conn, action_id, user.id, payload.idempotency_key, materialized_ref,
        )
        copilot_repo.add_event(
            conn,
            session["id"],
            user.id,
            {
                "event_type": "action_item",
                "content": action["title"],
                "recommendation": f"Materializado em {action['action_type']}.",
                "source_refs": [{"kind": "materialized_ref", **materialized_ref}],
            },
        )
        refreshed = _find(conn, session["id"])
        context = refreshed["knowledge_snapshot"] or copilot_repo.get_knowledge_context(
            conn,
            refreshed["workspace_id"],
            refreshed["proposal_id"],
            refreshed.get("opportunity_id"),
        )
        copilot_repo.upsert_journey_snapshot(
            conn,
            refreshed["id"],
            _build_journey_snapshot(
                refreshed,
                context,
                [dict(item) for item in copilot_repo.list_actions(conn, refreshed["id"])],
                "derived",
            ),
        )
        return _session(conn, refreshed)


def complete_session(
    session_id: UUID,
    payload: SalesCopilotCompleteRequest,
    user: CurrentUserResponse,
) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        row = _find(conn, session_id, for_update=True)
        if row["status"] == "completed":
            return _session(conn, row)
        transcript = row["transcript"].strip()
        participants = jsonable_encoder(
            [dict(item) for item in copilot_repo.list_participants(conn, session_id)]
        )
        context = row["knowledge_snapshot"] or copilot_repo.get_knowledge_context(
            conn, row["workspace_id"], row["proposal_id"], row.get("opportunity_id"),
        )
        context = jsonable_encoder(context)
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Inclua a transcrição ou notas antes de concluir.",
        )
    ai_result = execute_squad_pipeline_safe(
        pilar="conversao",
        squad_key="sales_copilot",
        input_context={
            "objective": f"Resumir reunião comercial: {row['title']}",
            "project_title": row["title"],
            "project_description": transcript[-20_000:],
            "participants": participants,
            "knowledge_context": context,
            "source": "sales_copilot_post_call",
        },
        requested_by_user_id=str(user.id),
    )
    output = ai_result["output_data"]
    action_candidates = _action_candidates(output)
    summary = (
        output.get("script_fechamento")
        or output.get("summary")
        or f"Reunião concluída com {len(transcript.split())} palavras registradas."
    )
    with connect() as conn:
        _find(conn, session_id, for_update=True)
        completed = copilot_repo.complete_session(conn, session_id, payload.duration_seconds, str(summary))
        copilot_repo.add_event(
            conn,
            session_id,
            user.id,
            {
                "event_type": "insight",
                "content": str(summary),
                "recommendation": "Revisar os compromissos antes de materializá-los.",
                "source_refs": [{"kind": "transcript", "generation_mode": ai_result["generation_mode"]}],
            },
        )
        for index, item in enumerate(action_candidates, start=1):
            copilot_repo.add_action(
                conn,
                session_id,
                user.id,
                {
                    **item,
                    "idempotency_key": f"analysis-{session_id}-{index}",
                    "source_refs": [{"kind": "transcript", "generation_mode": ai_result["generation_mode"]}],
                },
            )
        if completed.get("workspace_id") and not completed.get("opportunity_id"):
            registration = {
                "action_type": "opportunity_registration",
                "title": f"Registrar oportunidade: {completed['title']}",
                "detail": str(summary),
                "owner_hint": None,
                "due_at": None,
                "idempotency_key": f"opportunity-registration:{session_id}",
                "source_refs": [{"kind": "sales_copilot_session", "id": str(session_id)}],
            }
            copilot_repo.add_action(conn, session_id, user.id, registration)
            action_candidates.append(registration)
        copilot_repo.upsert_journey_snapshot(
            conn,
            session_id,
            _build_journey_snapshot(completed, context, action_candidates, ai_result["generation_mode"]),
        )
        if completed.get("opportunity_id"):
            proposals_repo.create_commercial_activity(
                conn,
                completed["opportunity_id"],
                {
                    "activity_type": "meeting_completed",
                    "title": completed["title"],
                    "body": str(summary),
                    "source_kind": "sales_copilot",
                    "source_ref": str(session_id),
                    "idempotency_key": f"meeting-completed:{session_id}",
                    "metadata": {
                        "session_id": str(session_id),
                        "generation_mode": ai_result["generation_mode"],
                        "duration_seconds": payload.duration_seconds,
                    },
                },
                user.id,
            )
        return _session(conn, completed)


def rebuild_journey(session_id: UUID, user: CurrentUserResponse) -> SalesCopilotSession:
    require_platform_admin(user)
    with connect() as conn:
        row = _find(conn, session_id, for_update=True)
        context = row["knowledge_snapshot"] or copilot_repo.get_knowledge_context(
            conn, row["workspace_id"], row["proposal_id"], row.get("opportunity_id"),
        )
        actions = [dict(item) for item in copilot_repo.list_actions(conn, session_id)]
        copilot_repo.upsert_journey_snapshot(
            conn, session_id, _build_journey_snapshot(row, context, actions, "derived")
        )
        return _session(conn, _find(conn, session_id))


def metrics(user: CurrentUserResponse) -> SalesCopilotMetrics:
    require_platform_admin(user)
    with connect() as conn:
        return SalesCopilotMetrics(**copilot_repo.metrics(conn))


def realtime_adapter_status(user: CurrentUserResponse) -> RealtimeAdapterStatus:
    require_platform_admin(user)
    return RealtimeAdapterStatus(
        available=True,
        status="adapter_ready",
        message=(
            "Ingestão diarizada, contexto e sugestões ao vivo estão prontos. "
            "A entrada automática no Meet/Teams ainda exige conectar um provedor de bot/transcrição."
        ),
        supported_input=[
            "manual_transcript",
            "transcript_upload",
            "diarized_segment_batch",
            "meeting_notes",
            "live_context_analysis",
            "post_call_analysis",
        ],
        supported_meeting_providers=["manual", "google_meet", "microsoft_teams"],
        transport="polling",
    )


def _find(conn, session_id: UUID, *, for_update: bool = False):
    row = copilot_repo.get_session(conn, session_id, for_update=for_update)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada.")
    return row


def _find_open_session(conn, session_id: UUID):
    session = _find(conn, session_id, for_update=True)
    if session["status"] in {"completed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A sessão já foi encerrada.")
    return session


def _session(conn, row) -> SalesCopilotSession:
    snapshot = copilot_repo.get_journey_snapshot(conn, row["id"])
    return SalesCopilotSession(
        **dict(row),
        events=[SalesCopilotEvent(**event) for event in copilot_repo.list_events(conn, row["id"])],
        participants=[
            SalesCopilotParticipant(**participant)
            for participant in copilot_repo.list_participants(conn, row["id"])
        ],
        segments=[
            SalesCopilotTranscriptSegment(**segment)
            for segment in copilot_repo.list_segments(conn, row["id"])
        ],
        suggestions=[
            SalesCopilotLiveSuggestion(**suggestion)
            for suggestion in copilot_repo.list_suggestions(conn, row["id"])
        ],
        actions=[
            SalesCopilotAction(**action)
            for action in copilot_repo.list_actions(conn, row["id"])
        ],
        journey_snapshot=SalesJourneySnapshot(**snapshot) if snapshot else None,
    )


def _action_candidates(output: dict) -> list[dict]:
    raw_items = output.get("action_items") or output.get("next_steps") or []
    if not isinstance(raw_items, list):
        return []
    candidates = []
    for item in raw_items[:20]:
        if isinstance(item, str) and item.strip():
            candidates.append({
                "action_type": "follow_up_task",
                "title": item.strip()[:500],
                "detail": None,
                "owner_hint": None,
                "due_at": None,
            })
        elif isinstance(item, dict) and str(item.get("title") or "").strip():
            action_type = item.get("action_type", "follow_up_task")
            if action_type not in {"follow_up_task", "proposal_revision", "project_update", "opportunity_registration"}:
                action_type = "follow_up_task"
            candidates.append({
                "action_type": action_type,
                "title": str(item["title"]).strip()[:500],
                "detail": str(item.get("detail") or "")[:10_000] or None,
                "owner_hint": str(item.get("owner") or "")[:255] or None,
                "due_at": None,
            })
    return candidates


def _materialize_action_in_transaction(conn, session, action, user: CurrentUserResponse) -> dict:
    if action["action_type"] == "opportunity_registration":
        if not session["workspace_id"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selecione o workspace do cliente antes de registrar a oportunidade.",
            )
        if session.get("opportunity_id"):
            return {"kind": "opportunity", "id": str(session["opportunity_id"]), "idempotent": True}
        opportunity = proposals_repo.create_opportunity(
            conn,
            {
                "workspace_id": session["workspace_id"],
                "owner_user_id": user.id,
                "source_platform": "sales_copilot",
                "external_id": str(session["id"]),
                "title": session["title"],
                "description": action.get("detail") or session.get("participant_context"),
                "status": "evaluating",
                "raw_payload": {"session_id": str(session["id"]), "action_id": str(action["id"])},
            },
        )
        copilot_repo.link_opportunity(conn, session["id"], opportunity["id"])
        return {"kind": "opportunity", "id": str(opportunity["id"]), "workspace_id": str(session["workspace_id"])}
    if action["action_type"] == "follow_up_task":
        if not session["workspace_id"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Vincule a sessão a um cliente para criar o follow-up.",
            )
        task_list = conn.execute(
            """
            select id from eg_task_lists
            where workspace_id = %s and type = 'general'
            order by created_at
            limit 1
            """,
            (session["workspace_id"],),
        ).fetchone()
        if not task_list:
            task_list = tasks_repo.create_task_list(
                conn, session["workspace_id"], "Follow-ups comerciais", "general",
            )
        task = tasks_repo.create_task(
            conn,
            task_list["id"],
            {
                "title": action["title"],
                "description": action["detail"],
                "status": "A fazer",
                "group_status": "NOT_STARTED",
                "priority": "Alta",
                "due_date": action["due_at"],
                "recurrence": "none",
            },
        )
        return {"kind": "task", "id": str(task["id"]), "list_id": str(task_list["id"])}
    if action["action_type"] == "proposal_revision":
        if not session["proposal_id"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Vincule a sessão a uma proposta para criar uma revisão.",
            )
        revision = lifecycle_repo.create_revision(conn, session["proposal_id"])
        if not revision:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta não encontrada.")
        lifecycle_repo.record_event(
            conn,
            revision["id"],
            "proposal.revision_from_meeting",
            user.id,
            {"session_id": str(session["id"]), "action_id": str(action["id"])},
        )
        return {"kind": "proposal_revision", "id": str(revision["id"]), "version": revision["version"]}
    context = copilot_repo.get_knowledge_context(
        conn, session["workspace_id"], session["proposal_id"], session.get("opportunity_id")
    )
    conversion = context.get("conversion")
    if not conversion:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A proposta ainda não foi convertida em projeto.",
        )
    update = projects_repo.create_project_update(
        conn,
        conversion["project_id"],
        user.id,
        {
            "kind": "progress",
            "summary": action["title"],
            "detail": action["detail"],
            "client_visible": False,
        },
    )
    return {
        "kind": "project_update",
        "id": str(update["id"]),
        "project_id": str(conversion["project_id"]),
    }


def _build_journey_snapshot(session: dict, context: dict, actions: list[dict], generation_mode: str) -> dict:
    opportunity = context.get("opportunity") or {}
    proposal = context.get("proposal") or {}
    conversion = context.get("conversion") or {}
    has_workspace = bool(session.get("workspace_id"))
    has_opportunity = bool(session.get("opportunity_id") or opportunity)
    has_proposal = bool(session.get("proposal_id") or proposal)
    won = opportunity.get("status") == "won" or proposal.get("status") == "won" or bool(conversion)

    if won:
        current_stage, bottleneck_stage = "post_sale", "advocate"
        bottleneck = "Consolidar onboarding, valor entregue, recorrência e indicação."
    elif has_proposal:
        current_stage, bottleneck_stage = "conversion", "act"
        bottleneck = "Transformar proposta em decisão com valor, responsáveis e próximo passo explícitos."
    elif has_opportunity:
        current_stage, bottleneck_stage = "diagnosis", "ask"
        bottleneck = "Estruturar diagnóstico, prova e critérios de avanço antes de gerar a proposta."
    elif has_workspace:
        current_stage, bottleneck_stage = "capture", "ask"
        bottleneck = "Registrar a oportunidade e qualificar dor, impacto, decisão e prazo."
    else:
        current_stage, bottleneck_stage = "acquisition", "aware"
        bottleneck = "Identificar o cliente e vinculá-lo a um workspace antes de avançar o funil."

    funnel_def = [
        ("acquisition", "Aquisição", True),
        ("capture", "Captação", has_workspace),
        ("diagnosis", "Diagnóstico", has_opportunity),
        ("conversion", "Conversão", has_proposal),
        ("post_sale", "Pós-venda", won),
    ]
    reached_current = False
    funnel_map = []
    for key, label, completed in funnel_def:
        if key == current_stage:
            state = "current"
            reached_current = True
        elif completed and not reached_current:
            state = "completed"
        else:
            state = "not_started"
        funnel_map.append({"key": key, "label": label, "state": state})

    stage_inputs = [
        ("aware", "Aware", has_opportunity or has_workspace),
        ("appeal", "Appeal", bool(session.get("transcript"))),
        ("ask", "Ask", has_proposal),
        ("act", "Act", won),
        ("advocate", "Advocate", won),
    ]
    order = [key for key, _, _ in stage_inputs]
    current_index = order.index(bottleneck_stage)
    journey_stages = []
    for index, (key, label, completed) in enumerate(stage_inputs):
        state = "current" if index == current_index else "completed" if completed and index < current_index else "not_started"
        journey_stages.append({"key": key, "label": label, "state": state, "score": None})

    recommendations = []
    for action in actions[:10]:
        title = str(action.get("title") or "").strip()
        if title:
            recommendations.append({"title": title, "type": action.get("action_type", "follow_up_task")})
    if not recommendations:
        recommendations.append({"title": bottleneck, "type": "next_step"})

    evidence_refs = [{"kind": "sales_copilot_session", "id": str(session["id"])}]
    if session.get("opportunity_id"):
        evidence_refs.append({"kind": "opportunity", "id": str(session["opportunity_id"])})
    if session.get("proposal_id"):
        evidence_refs.append({"kind": "proposal", "id": str(session["proposal_id"])})
    return {
        "workspace_id": session.get("workspace_id"),
        "opportunity_id": session.get("opportunity_id"),
        "current_funnel_stage": current_stage,
        "funnel_map": funnel_map,
        "journey_stages": journey_stages,
        "scores": {"offer": None, "demand": None, "conversion": None, "note": "Sem nota inventada; preencher a partir do Raio-X comercial."},
        "bottlenecks": [{"stage": bottleneck_stage, "title": bottleneck, "severity": "high"}],
        "recommended_actions": recommendations,
        "evidence_refs": evidence_refs,
        "generation_mode": generation_mode,
    }


def _validate_context(
    workspace_id: UUID | None,
    proposal_id: UUID | None,
    context: dict,
    opportunity_id: UUID | None = None,
) -> None:
    if workspace_id and "client" not in context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente ativo não encontrado.")
    if proposal_id and "proposal" not in context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta não encontrada.")
    if opportunity_id and "opportunity" not in context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")
    if workspace_id and opportunity_id and context["opportunity"].get("workspace_id") != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A oportunidade não pertence ao cliente selecionado.",
        )
    if workspace_id and proposal_id:
        proposal_workspace_id = context["proposal"].get("workspace_id")
        if proposal_workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A proposta não pertence ao cliente selecionado.",
            )


def list_fathom_meetings(user: CurrentUserResponse, limit: int = 20) -> list[FathomMeeting]:
    """Reuniões gravadas no Fathom, para escolher qual importar."""
    require_platform_admin(user)
    try:
        meetings = list_fathom_meetings_safe(limit=limit)
    except RuntimeError as exc:
        # Chave ausente: mensagem real, não lista vazia disfarçada de "sem reuniões".
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível consultar as reuniões no Fathom.",
        ) from exc
    return [FathomMeeting(**meeting) for meeting in meetings]


def import_fathom_meeting(
    session_id: UUID,
    payload: FathomImportRequest,
    user: CurrentUserResponse,
) -> FathomImportResult:
    """Traz a transcrição real do Fathom para uma sessão do copiloto.

    Mantém a mesma exigência de consentimento das outras fontes automáticas: o
    Fathom já gravou com aviso na call, mas o registro que vale para auditoria é
    o do Bioma.
    """
    require_platform_admin(user)
    with connect() as conn:
        session = _find_open_session(conn, session_id)
        if session["consent_status"] != "granted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registre o consentimento da sessão antes de importar a transcrição.",
            )

    try:
        segments = get_fathom_transcript_safe(payload.recording_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível baixar a transcrição desta gravação no Fathom.",
        ) from exc

    if not segments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A gravação não tem transcrição disponível no Fathom.",
        )

    imported = 0
    with connect() as conn:
        # Limite alto explícito em vez de None: a checagem de idempotência precisa
        # ver a sessão inteira, e um NULL implícito no LIMIT é fácil de quebrar.
        existing = {row["idempotency_key"] for row in copilot_repo.list_segments(conn, session_id, 5000)}
        for segment in segments:
            # Reimportar a mesma reunião não duplica: a chave inclui gravação+posição.
            if segment["idempotency_key"] in existing:
                continue
            copilot_repo.add_segment(conn, session_id, user.id, segment)
            imported += 1
        copilot_repo.add_event(
            conn,
            session_id,
            user.id,
            {
                "event_type": "note",
                "content": f"Transcrição importada do Fathom (gravação {payload.recording_id}).",
                "recommendation": f"{imported} segmento(s) novo(s) ingerido(s).",
                "source_refs": [],
            },
        )

    analyzed = False
    if payload.analyze_after_import and imported > 0:
        analyze_live(session_id, SalesCopilotLiveAnalyzeRequest(), user)
        analyzed = True

    return FathomImportResult(
        session_id=session_id,
        recording_id=payload.recording_id,
        imported_segments=imported,
        skipped_segments=len(segments) - imported,
        analyzed=analyzed,
    )
