from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from uuid import uuid4

import pytest
from fastapi import HTTPException

from bioma_api.schemas.sales_copilot import (
    SalesCopilotActionMaterialize,
    SalesCopilotCompleteRequest,
    SalesCopilotLiveAnalyzeRequest,
    SalesCopilotTranscriptBatch,
    SalesCopilotTranscriptSegmentCreate,
)
from bioma_api.services import sales_copilot as copilot_service


def _session_row(**overrides):
    now = datetime.now(timezone.utc)
    row = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "proposal_id": None,
        "opportunity_id": None,
        "title": "Discovery",
        "session_type": "discovery",
        "language": "pt-BR",
        "status": "prepared",
        "realtime_status": "adapter_ready",
        "objective": "Entender o cenário",
        "participant_context": None,
        "meeting_provider": "google_meet",
        "meeting_url": "https://meet.google.com/example",
        "external_meeting_id": None,
        "consent_status": "granted",
        "consent_recorded_at": now,
        "retention_until": now,
        "live_context": {},
        "knowledge_snapshot": {"client": {"organization_name": "Cliente"}},
        "preparation_brief": {},
        "transcript": "",
        "summary": None,
        "duration_seconds": 0,
        "created_by": uuid4(),
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    row.update(overrides)
    return row


def test_external_transcript_requires_recorded_consent(eg_admin, monkeypatch):
    session = _session_row(consent_status="pending")

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(copilot_service, "connect", fake_connect)
    monkeypatch.setattr(copilot_service, "_find_open_session", lambda *_args: session)
    monkeypatch.setattr(copilot_service.copilot_repo, "list_participants", lambda *_args: [])

    with pytest.raises(HTTPException) as exc:
        copilot_service.ingest_transcript(
            session["id"],
            SalesCopilotTranscriptBatch(segments=[
                SalesCopilotTranscriptSegmentCreate(
                    idempotency_key="meet-segment-1",
                    source="google_meet",
                    content="Trecho capturado pelo adaptador.",
                ),
            ]),
            eg_admin,
        )

    assert exc.value.status_code == 409
    assert "consentimento" in exc.value.detail.lower()


def test_transcript_rejects_participant_from_another_session(eg_admin, monkeypatch):
    session = _session_row()

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(copilot_service, "connect", fake_connect)
    monkeypatch.setattr(copilot_service, "_find_open_session", lambda *_args: session)
    monkeypatch.setattr(copilot_service.copilot_repo, "list_participants", lambda *_args: [])

    with pytest.raises(HTTPException) as exc:
        copilot_service.ingest_transcript(
            session["id"],
            SalesCopilotTranscriptBatch(segments=[
                SalesCopilotTranscriptSegmentCreate(
                    idempotency_key="manual-segment-1",
                    participant_id=uuid4(),
                    content="Participante incorreto.",
                ),
            ]),
            eg_admin,
        )

    assert exc.value.status_code == 422
    assert "não pertence" in exc.value.detail


def test_live_analysis_runs_without_open_database_transaction(eg_admin, monkeypatch):
    session = _session_row()
    segment_id = uuid4()
    open_connections = 0
    saved = {}

    @contextmanager
    def fake_connect():
        nonlocal open_connections
        open_connections += 1
        try:
            yield object()
        finally:
            open_connections -= 1

    def fake_analyze(request):
        assert open_connections == 0
        assert request["knowledge_context"]["client"]["organization_name"] == "Cliente"
        return {
            "generation_mode": "live",
            "output": {"moment": "objection_price", "suggested_line": "Pergunte quem aprova o orçamento."},
        }

    monkeypatch.setattr(copilot_service, "connect", fake_connect)
    monkeypatch.setattr(copilot_service, "_find", lambda *_args, **_kwargs: session)
    monkeypatch.setattr(
        copilot_service.copilot_repo,
        "list_segments",
        lambda *_args: [{
            "id": segment_id,
            "speaker_label": "CFO",
            "content": "O orçamento está caro.",
        }],
    )
    monkeypatch.setattr(copilot_service.copilot_repo, "list_participants", lambda *_args: [])
    # `analyze_live` usa o caminho dedicado (analyze_sales_live_window_safe),
    # não o squad genérico — mockar execute_squad_pipeline_safe (como este
    # teste fazia) nunca exercitava o código real: a asserção sobre
    # suggestion_type só passava por coincidência do fallback de prévia local.
    monkeypatch.setattr(copilot_service, "analyze_sales_live_window_safe", fake_analyze)
    monkeypatch.setattr(
        copilot_service.copilot_repo,
        "add_suggestion",
        lambda _conn, _session_id, data: saved.update(data),
    )
    monkeypatch.setattr(copilot_service, "_session", lambda _conn, row: row["id"])

    result = copilot_service.analyze_live(
        session["id"],
        SalesCopilotLiveAnalyzeRequest(window_segments=12),
        eg_admin,
    )

    assert result == session["id"]
    assert saved["suggestion_type"] == "objection_response"
    assert saved["generation_mode"] == "live"
    assert saved["source_refs"] == [{"kind": "transcript_segment", "id": str(segment_id)}]


def test_materialized_action_replay_is_idempotent(eg_admin, monkeypatch):
    session = _session_row()
    action = {
        "id": uuid4(),
        "session_id": session["id"],
        "status": "materialized",
        "idempotency_key": "copilot-action-replay",
    }

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(copilot_service, "connect", fake_connect)
    monkeypatch.setattr(copilot_service.copilot_repo, "get_action", lambda *_args, **_kwargs: action)
    monkeypatch.setattr(copilot_service, "_find", lambda *_args, **_kwargs: session)
    monkeypatch.setattr(copilot_service, "_session", lambda _conn, row: row["id"])
    monkeypatch.setattr(
        copilot_service,
        "_materialize_action_in_transaction",
        lambda *_args: pytest.fail("replay não pode materializar novamente"),
    )

    assert copilot_service.materialize_action(
        action["id"],
        SalesCopilotActionMaterialize(confirm=True, idempotency_key="copilot-action-replay"),
        eg_admin,
    ) == session["id"]


def test_realtime_status_is_honest_about_meet_teams_adapter(eg_admin):
    status_result = copilot_service.realtime_adapter_status(eg_admin)

    assert status_result.available is True
    assert status_result.transport == "polling"
    assert set(status_result.supported_meeting_providers) == {
        "manual", "google_meet", "microsoft_teams",
    }
    assert "ainda exige" in status_result.message


def test_external_adapter_ingestion_uses_rotatable_token(monkeypatch):
    token = "meeting-adapter-secret"
    session = _session_row(ingest_token_hash=hashlib.sha256(token.encode()).hexdigest())
    captured = []

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(copilot_service, "connect", fake_connect)
    monkeypatch.setattr(copilot_service, "_find_open_session", lambda *_args: session)
    monkeypatch.setattr(
        copilot_service.copilot_repo,
        "add_segment",
        lambda _conn, session_id, actor_id, data: captured.append((session_id, actor_id, data)),
    )
    payload = SalesCopilotTranscriptBatch(segments=[
        SalesCopilotTranscriptSegmentCreate(
            idempotency_key="provider-segment-1",
            source="google_meet",
            external_speaker_id="speaker-1",
            speaker_label="CEO",
            content="Precisamos resolver isso neste trimestre.",
        ),
    ])

    ack = copilot_service.ingest_external_transcript(session["id"], payload, token)

    assert ack.accepted_segments == 1
    assert captured[0][0] == session["id"]
    assert captured[0][1] is None
    assert captured[0][2]["external_speaker_id"] == "speaker-1"


def test_issue_ingestion_credential_only_rotates_adapter_token(eg_admin, monkeypatch):
    session = _session_row()
    events = []

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(copilot_service, "connect", fake_connect)
    monkeypatch.setattr(copilot_service, "_find_open_session", lambda *_args: session)
    monkeypatch.setattr(copilot_service.copilot_repo, "set_ingest_token_hash", lambda *_args: None)
    monkeypatch.setattr(copilot_service.copilot_repo, "add_event", lambda *_args: events.append(_args[-1]))

    credential = copilot_service.issue_ingestion_credential(session["id"], eg_admin)

    assert credential.session_id == session["id"]
    assert credential.ingest_token
    assert events[0]["content"] == "Credencial de ingestão rotacionada."


def test_complete_session_returns_meeting_to_opportunity_timeline(eg_admin, monkeypatch):
    opportunity_id = uuid4()
    session = _session_row(status="live", transcript="Conversa real da reunião.", opportunity_id=opportunity_id)
    completed = {**session, "status": "completed", "summary": "Resumo confirmado."}
    activities = []

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(copilot_service, "connect", fake_connect)
    monkeypatch.setattr(copilot_service, "_find", lambda *_args, **_kwargs: session)
    monkeypatch.setattr(copilot_service, "execute_squad_pipeline_safe", lambda **_kwargs: {
        "output_data": {"summary": "Resumo confirmado.", "action_items": []},
        "generation_mode": "preview",
    })
    monkeypatch.setattr(copilot_service.copilot_repo, "list_participants", lambda *_args: [])
    monkeypatch.setattr(copilot_service.copilot_repo, "complete_session", lambda *_args: completed)
    monkeypatch.setattr(copilot_service.copilot_repo, "add_event", lambda *_args: None)
    monkeypatch.setattr(copilot_service.copilot_repo, "add_action", lambda *_args: None)
    monkeypatch.setattr(copilot_service.copilot_repo, "list_events", lambda *_args: [])
    monkeypatch.setattr(copilot_service.copilot_repo, "list_segments", lambda *_args: [])
    monkeypatch.setattr(copilot_service.copilot_repo, "list_suggestions", lambda *_args: [])
    monkeypatch.setattr(copilot_service.copilot_repo, "list_actions", lambda *_args: [])
    monkeypatch.setattr(copilot_service.copilot_repo, "get_journey_snapshot", lambda *_args: None)
    monkeypatch.setattr(copilot_service.copilot_repo, "upsert_journey_snapshot", lambda *_args: None)
    monkeypatch.setattr(
        copilot_service.proposals_repo,
        "create_commercial_activity",
        lambda _conn, _opportunity_id, payload, _user_id: activities.append((_opportunity_id, payload)),
    )

    result = copilot_service.complete_session(
        session["id"], SalesCopilotCompleteRequest(duration_seconds=900), eg_admin
    )

    assert result.status == "completed"
    assert activities[0][0] == opportunity_id
    assert activities[0][1]["activity_type"] == "meeting_completed"


def test_journey_snapshot_uses_pipeline_evidence_without_inventing_scores():
    session = _session_row(
        transcript="Cliente explicou a dor e pediu proposta.",
        opportunity_id=uuid4(),
        proposal_id=None,
    )
    snapshot = copilot_service._build_journey_snapshot(
        session,
        {"opportunity": {"status": "evaluating"}},
        [{"title": "Enviar diagnóstico", "action_type": "follow_up_task"}],
        "preview",
    )

    assert snapshot["current_funnel_stage"] == "diagnosis"
    assert snapshot["bottlenecks"][0]["stage"] == "ask"
    assert snapshot["scores"]["conversion"] is None
    assert snapshot["recommended_actions"][0]["title"] == "Enviar diagnóstico"


def test_external_adapter_rejects_invalid_token(monkeypatch):
    session = _session_row(ingest_token_hash=hashlib.sha256(b"correct").hexdigest())

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(copilot_service, "connect", fake_connect)
    monkeypatch.setattr(copilot_service, "_find_open_session", lambda *_args: session)

    with pytest.raises(HTTPException) as exc:
        copilot_service.ingest_external_transcript(
            session["id"],
            SalesCopilotTranscriptBatch(segments=[
                SalesCopilotTranscriptSegmentCreate(
                    idempotency_key="provider-segment-2",
                    source="microsoft_teams",
                    content="Trecho",
                ),
            ]),
            "wrong",
        )

    assert exc.value.status_code == 401
