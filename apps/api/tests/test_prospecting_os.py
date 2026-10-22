from datetime import datetime, timezone
from uuid import uuid4
import pytest
from unittest.mock import MagicMock

from bioma_api.repositories.prospecting import (
    DEFAULT_CANONICAL_CARDS,
    ProspectingRepository,
)
from bioma_api.schemas.prospecting import (
    CreateProspectingListRequest,
    HandoffPayload,
    ProspectingItemCreate,
    RecordDispositionRequest,
    SalesKnowledgeCardStatusUpdate,
    StartProspectingSessionRequest,
)
from bioma_api.services import prospecting as prospecting_service


class MockCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self._fetchone_val = fetchone_val
        self._fetchall_val = fetchall_val or []
        self.rowcount = 1

    def execute(self, sql, params=None):
        pass

    def fetchone(self):
        return self._fetchone_val

    def fetchall(self):
        return self._fetchall_val

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockConnection:
    def __init__(self, cursor_obj):
        self._cursor = cursor_obj

    def cursor(self, row_factory=None):
        return self._cursor

    def execute(self, sql, params=None):
        return self._cursor


def test_canonical_seed_contains_essential_battlecards():
    codes = {c["code"] for c in DEFAULT_CANONICAL_CARDS}
    assert "C001" in codes  # Diagnosticar antes de prescrever
    assert "C021" in codes  # Preço cedo
    assert "C025" in codes  # Já temos uma agência
    assert "C027" in codes  # Está caro
    assert "C033" in codes  # Já tentamos IA
    assert "C034" in codes  # Nosso ERP já faz isso
    assert "C056" in codes  # Handoff Estruturado

    # Verify C025 Battlecard
    c025 = next(c for c in DEFAULT_CANONICAL_CARDS if c["code"] == "C025")
    assert "já tenho agência" in c025["aliases"]
    assert "Hoje essa agência atua mais em mídia" in c025["ask_first"]
    assert len(c025["avoid"]) > 0


def test_crm_ownership_conflicts_detection():
    repo = ProspectingRepository()
    mock_lead = {
        "id": uuid4(),
        "name": "Dra. Camila",
        "company": "Clínica Sorriso",
        "phone": "11987654321",
        "stage": "qualifying",
        "updated_at": datetime.now(timezone.utc),
    }

    cur = MockCursor(fetchall_val=[mock_lead])
    conn = MockConnection(cur)

    conflicts = repo.check_crm_ownership_conflicts(
        conn,
        workspace_id=uuid4(),
        phones=["11987654321", "11999999999"],
        companies=["Clínica Sorriso", "Outra Empresa"],
    )

    assert "11987654321" in conflicts
    assert conflicts["11987654321"]["has_conflict"] is True
    assert "CRM no estágio 'qualifying'" in conflicts["11987654321"]["warning_label"]


def test_record_disposition_metrics_and_handoff():
    repo = ProspectingRepository()
    session_id = uuid4()
    item_id = uuid4()

    mock_event = {"id": uuid4(), "disposition": "meeting_scheduled"}
    mock_updated_item = {
        "id": item_id,
        "company_name": "Tech Corp",
        "contact_name": "Dr. Roberto",
        "status": "completed",
        "attempts_count": 1,
    }
    mock_updated_session = {
        "id": session_id,
        "completed_calls": 1,
        "connections_count": 1,
        "conversations_count": 1,
        "meetings_booked": 1,
        "follow_ups_count": 0,
    }

    # Sequence of fetchone results: item, session
    cur = MockCursor()
    fetch_results = [mock_updated_item, mock_updated_session]
    cur.fetchone = lambda: fetch_results.pop(0) if fetch_results else None
    conn = MockConnection(cur)

    handoff = {
        "problem": "Falta de previsibilidade em aquisição",
        "impact": "Faturamento oscila 40% mês a mês",
        "motion": "growth",
        "meeting_at": "2026-10-25 14:00",
    }

    result = repo.record_disposition(
        conn,
        session_id=session_id,
        item_id=item_id,
        disposition="meeting_scheduled",
        notes="Excelente abertura para escala comercial",
        handoff_payload=handoff,
    )

    assert result["session"]["completed_calls"] == 1
    assert result["session"]["meetings_booked"] == 1
    assert result["item"]["status"] == "completed"


def test_record_unanswered_disposition():
    repo = ProspectingRepository()
    session_id = uuid4()
    item_id = uuid4()

    mock_event = {"id": uuid4(), "disposition": "unanswered"}
    mock_updated_item = {
        "id": item_id,
        "company_name": "Tech Corp",
        "status": "pending",
        "attempts_count": 1,
    }
    mock_updated_session = {
        "id": session_id,
        "completed_calls": 1,
        "connections_count": 0,
        "conversations_count": 0,
        "meetings_booked": 0,
        "follow_ups_count": 0,
    }

    cur = MockCursor()
    fetch_results = [mock_updated_item, mock_updated_session]
    cur.fetchone = lambda: fetch_results.pop(0) if fetch_results else None
    conn = MockConnection(cur)

    result = repo.record_disposition(
        conn,
        session_id=session_id,
        item_id=item_id,
        disposition="unanswered",
        notes="Chamou até a caixa postal",
    )

    assert result["session"]["completed_calls"] == 1
    assert result["session"]["connections_count"] == 0
    assert result["session"]["meetings_booked"] == 0
    assert result["item"]["status"] == "pending"


def test_record_disposition_resilient_datetime_validator():
    # 1. Valid ISO string
    req1 = RecordDispositionRequest(
        item_id=uuid4(),
        disposition="follow_up",
        scheduled_follow_up_at="2026-10-25T14:30:00Z",
    )
    assert req1.scheduled_follow_up_at is not None
    assert req1.scheduled_follow_up_at.year == 2026

    # 2. Free text / non-ISO date should not raise 422, returns None gracefully
    req2 = RecordDispositionRequest(
        item_id=uuid4(),
        disposition="follow_up",
        scheduled_follow_up_at="Amanhã 15h",
    )
    assert req2.scheduled_follow_up_at is None

    # 3. None or empty string
    req3 = RecordDispositionRequest(
        item_id=uuid4(),
        disposition="follow_up",
        scheduled_follow_up_at=None,
    )
    assert req3.scheduled_follow_up_at is None


def test_queue_rotation_order_in_repository():
    # Verify that get_session SQL query orders pending leads by attempts_count and last_attempt_at
    executed_queries = []

    class CapturingCursor:
        def __init__(self):
            self._session_row = {"id": uuid4(), "list_id": uuid4()}
            self._items = []

        def execute(self, sql, params=None):
            executed_queries.append(sql)

        def fetchone(self):
            return self._session_row

        def fetchall(self):
            return self._items

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    cur = CapturingCursor()
    conn = MockConnection(cur)
    repo = ProspectingRepository()
    repo.get_session(conn, session_id=uuid4())

    items_query = next((q for q in executed_queries if "from prospecting_list_items" in q), "")
    assert "attempts_count asc" in items_query
    assert "last_attempt_at asc nulls first" in items_query
