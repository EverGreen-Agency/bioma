from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from bioma_api.services import proposal_lifecycle


def test_conversion_plan_draft_is_attached_after_worker_transaction(eg_admin, monkeypatch):
    proposal_id = uuid4()
    conversion_id = uuid4()
    project_id = uuid4()
    contract_id = uuid4()
    plan_id = uuid4()
    open_connections = 0
    attached = {}
    events = []

    @contextmanager
    def fake_connect():
        nonlocal open_connections
        open_connections += 1
        try:
            yield object()
        finally:
            open_connections -= 1

    def fake_generate(saved_project_id, payload, _user):
        assert open_connections == 0
        assert saved_project_id == project_id
        assert payload.contract_id == contract_id
        assert payload.source_kind == "contract"
        return SimpleNamespace(id=plan_id)

    monkeypatch.setattr(proposal_lifecycle, "connect", fake_connect)
    monkeypatch.setattr(
        proposal_lifecycle.lifecycle_repo,
        "attach_conversion_plan",
        lambda _conn, saved_conversion_id, saved_plan_id: attached.update(
            conversion_id=saved_conversion_id, plan_id=saved_plan_id,
        ),
    )
    monkeypatch.setattr(
        proposal_lifecycle.lifecycle_repo,
        "record_event",
        lambda _conn, _proposal_id, event_type, _actor, payload=None: events.append((event_type, payload)),
    )
    from bioma_api.services import projects as project_service
    monkeypatch.setattr(project_service, "generate_project_plan", fake_generate)

    proposal_lifecycle._generate_conversion_plan_draft(
        proposal_id,
        {
            "id": conversion_id,
            "project_id": project_id,
            "contract_id": contract_id,
        },
        {
            "problem_summary": "Baixa previsibilidade",
            "executive_summary": None,
            "content_markdown": "# Escopo",
            "special_requirements": "Tenant scope",
        },
        eg_admin,
    )

    assert attached == {"conversion_id": conversion_id, "plan_id": plan_id}
    assert events[-1][0] == "proposal.plan_draft_created"
