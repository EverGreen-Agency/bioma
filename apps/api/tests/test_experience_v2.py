from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.schemas.copilot import CopilotAction, CopilotSource
from bioma_api.schemas.work_graph import WorkEntityRef, WorkLinkCreate
from bioma_api.services import client_hub, copilot, work_graph


@contextmanager
def _connection():
    yield object()


def test_client_portal_prioritizes_client_attention_and_outcomes(eg_admin, monkeypatch):
    client_id, organization_id, workspace_id = uuid4(), uuid4(), uuid4()
    approval_id, delivery_id, blocked_id, request_id = uuid4(), uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc)

    monkeypatch.setattr(client_hub, "connect", _connection)
    monkeypatch.setattr(
        client_hub,
        "resolve_accessible_client",
        lambda *_args, **_kwargs: {
            "id": client_id, "organization_id": organization_id, "workspace_id": workspace_id,
        },
    )
    monkeypatch.setattr(
        client_hub_repo,
        "get_client_summary",
        lambda *_args: {
            "id": client_id, "organization_id": organization_id, "organization_name": "Cliente",
            "organization_slug": "cliente", "name": "Cliente", "status": "active",
            "responsible_name": "EG", "enabled_modules": ["hub"], "deliverables_total": 3,
            "approvals_pending": 1, "artifacts_client": 0,
        },
    )
    monkeypatch.setattr(client_hub_repo, "list_artifacts", lambda *_args: [])
    monkeypatch.setattr(
        client_hub_repo,
        "list_deliverables",
        lambda *_args: [
            {"id": delivery_id, "title": "Landing page", "status": "done", "due_at": None, "assignee_emails": [], "updated_at": now},
            {"id": uuid4(), "title": "Campanha", "status": "in_progress", "due_at": None, "assignee_emails": [], "updated_at": now},
            {"id": blocked_id, "title": "Integração", "status": "blocked", "due_at": now, "assignee_emails": [], "updated_at": now},
        ],
    )
    monkeypatch.setattr(
        client_hub_repo,
        "list_approvals",
        lambda *_args: [{"id": approval_id, "deliverable_id": delivery_id, "deliverable_title": "Landing page", "status": "pending", "comment": None, "created_at": now, "decided_at": None}],
    )
    monkeypatch.setattr(
        client_hub_repo,
        "list_client_requests",
        lambda *_args: [{
            "id": request_id, "category": "request", "title": "Enviar logo", "detail": None,
            "status": "waiting_client", "priority": "normal", "requested_by": eg_admin.id,
            "requested_by_name": "Teste", "assigned_to": None, "resolution_summary": "Precisamos do SVG.",
            "created_at": now, "updated_at": now,
        }],
    )
    monkeypatch.setattr(client_hub_repo, "list_sync_runs", lambda *_args: [])
    monkeypatch.setattr(client_hub_repo, "list_audit_logs", lambda *_args: [])

    portal = client_hub.get_client_portal(workspace_id, eg_admin)

    assert portal.progress.deliverables_total == 3
    assert portal.progress.deliverables_done == 1
    assert portal.progress.completion_percentage == 33
    assert [item.kind for item in portal.attention] == ["approval", "request", "delivery"]
    assert portal.requests[0].status == "waiting_client"


def test_typed_copilot_blocks_keep_answer_actions_and_sources_separate():
    action = CopilotAction(
        name="capture_opportunity", label="Criar oportunidade", params={}, why="briefing colado",
        status="executed", detail="Criada.",
    )
    source = CopilotSource(kind="bioma", reference="opportunity:123")

    blocks = copilot._response_blocks(
        "Rascunho revisável.", [action], [source], {"opportunity_id": "123"}
    )

    assert [block.kind for block in blocks] == ["markdown", "entity_summary", "action_list", "source_list"]
    assert blocks[0].data == {"text": "Rascunho revisável."}
    assert blocks[1].data["entity_type"] == "opportunity"


def test_work_graph_rejects_self_link_before_database(eg_admin):
    item_id = uuid4()
    payload = WorkLinkCreate(
        source=WorkEntityRef(type="work_item", id=item_id),
        relation="implements",
        target=WorkEntityRef(type="work_item", id=item_id),
    )

    with pytest.raises(HTTPException) as exc:
        work_graph.create_link(uuid4(), payload, eg_admin)

    assert exc.value.status_code == 422
    assert "si mesmo" in exc.value.detail
