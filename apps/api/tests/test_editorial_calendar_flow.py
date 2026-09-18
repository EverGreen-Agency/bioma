from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from bioma_api.services import editorial_calendar as service


@pytest.fixture
def calendar_context(monkeypatch):
    workspace_id, organization_id, item_id = uuid4(), uuid4(), uuid4()
    client = {"workspace_id": workspace_id, "organization_id": organization_id}
    state = {"stage": "review", "scheduled_at": None, "post_text": "Legenda revisada"}
    calls = []

    @contextmanager
    def connection():
        yield object()

    monkeypatch.setattr(service, "connect", connection)
    monkeypatch.setattr(service, "_accessible_workspace", lambda conn, wid, user, capability=None: client)
    monkeypatch.setattr(service.cal_repo, "get_calendar_item_for_update", lambda conn, wid, iid: state)
    monkeypatch.setattr(service.cal_repo, "update_calendar_stage", lambda conn, wid, iid, stage: calls.append(stage) or None)
    monkeypatch.setattr(service, "_audit", lambda *args: None)
    monkeypatch.setattr(service, "require_workspace_capability", lambda conn, user, capability: calls.append(capability))
    user = type("User", (), {"id": uuid4()})()
    return workspace_id, item_id, user, state, calls


def test_publicacao_manual_nao_e_permitida(calendar_context):
    workspace_id, item_id, user, state, calls = calendar_context
    with pytest.raises(HTTPException) as error:
        service.update_stage(workspace_id, item_id, "published", user)
    assert error.value.status_code == 409
    assert "published" not in calls


def test_aprovacao_exige_texto(calendar_context):
    workspace_id, item_id, user, state, calls = calendar_context
    state["post_text"] = " "
    with pytest.raises(HTTPException) as error:
        service.update_stage(workspace_id, item_id, "approved", user)
    assert error.value.status_code == 422
    assert "approved" not in calls


def test_agendamento_exige_data_futura(calendar_context):
    workspace_id, item_id, user, state, calls = calendar_context
    state["stage"] = "approved"
    state["scheduled_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    with pytest.raises(HTTPException) as error:
        service.update_stage(workspace_id, item_id, "scheduled", user)
    assert error.value.status_code == 422
    assert "scheduled" not in calls


def test_aprovador_nao_pode_cancelar_agendamento(calendar_context, monkeypatch):
    workspace_id, item_id, user, state, calls = calendar_context
    state["stage"] = "scheduled"
    def require(conn, actor, capability):
        if capability != "approve":
            raise HTTPException(status_code=403, detail="Papel insuficiente")
    monkeypatch.setattr(service, "require_workspace_capability", require)
    with pytest.raises(HTTPException) as error:
        service.update_stage(workspace_id, item_id, "approved", user)
    assert error.value.status_code == 403
    assert "approved" not in calls


def test_importacao_de_ia_usa_saida_canonica_do_mesmo_workspace(monkeypatch):
    workspace_id, request_id = uuid4(), uuid4()
    def get_source(conn, wid, rid):
        assert wid == workspace_id and rid == request_id
        return {"output": {"posts": [{"title": "Peça real", "channel": "linkedin", "caption": "Texto rastreado"}]},
                "generation_mode": "live", "provider": "anthropic", "model": "claude"}
    monkeypatch.setattr(service.cal_repo, "get_ready_ai_content_request", get_source)
    payload = {"title": "Título forjado", "channel": "instagram", "post_text": "Texto forjado", "stage": "ideation",
               "metadata": {"source_type": "ai_content_request", "ai_content_request_id": str(request_id),
                            "output_index": 0, "provider": "provedor forjado"}}
    result = service._canonical_create_payload(object(), workspace_id, payload)
    assert (result["title"], result["channel"], result["post_text"]) == ("Peça real", "linkedin", "Texto rastreado")
    assert result["metadata"]["provider"] == "anthropic"


def test_importacao_de_ia_rejeita_origem_ausente(monkeypatch):
    monkeypatch.setattr(service.cal_repo, "get_ready_ai_content_request", lambda conn, wid, rid: None)
    payload = {"metadata": {"source_type": "ai_content_request", "ai_content_request_id": str(uuid4()), "output_index": 0}}
    with pytest.raises(HTTPException) as error:
        service._canonical_create_payload(object(), uuid4(), payload)
    assert error.value.status_code == 422
