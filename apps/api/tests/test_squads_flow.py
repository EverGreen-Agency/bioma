from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from bioma_api.schemas.squads import RunSquadPayload
from bioma_api.services import squads as squads_service


def test_squad_execution_closes_database_during_provider_call(eg_admin, monkeypatch):
    workspace_id = uuid4()
    organization_id = uuid4()
    execution_id = uuid4()
    open_connections = 0

    @contextmanager
    def fake_connect():
        nonlocal open_connections
        open_connections += 1
        try:
            yield object()
        finally:
            open_connections -= 1

    def fake_accessible_workspace(_conn, requested_workspace_id, _user, capability=None):
        assert requested_workspace_id == workspace_id
        assert capability == "generate_content"
        return {
            "workspace_id": workspace_id,
            "organization_id": organization_id,
        }

    def fake_execute(**_kwargs):
        assert open_connections == 0
        now = datetime.now(timezone.utc)
        return {
            "output_data": {"initial_deliverables": ["Reunião de kickoff"]},
            "generation_mode": "preview",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "estimated_cost_cents": 0,
            "execution_logs": [],
            "completed_at": now.isoformat(),
        }

    def fake_create_execution(_conn, resolved_workspace_id, payload):
        assert open_connections == 1
        assert resolved_workspace_id == workspace_id
        assert payload["generation_mode"] == "preview"
        now = datetime.now(timezone.utc)
        return {
            **payload,
            "id": execution_id,
            "workspace_id": workspace_id,
            "started_at": now,
            "completed_at": now,
        }

    monkeypatch.setattr(squads_service, "connect", fake_connect)
    monkeypatch.setattr(squads_service, "_accessible_workspace", fake_accessible_workspace)
    monkeypatch.setattr(squads_service.squads_repo, "get_squad_definition", lambda *_args: None)
    monkeypatch.setattr(squads_service, "execute_squad_pipeline_safe", fake_execute)
    monkeypatch.setattr(squads_service.squads_repo, "create_execution", fake_create_execution)
    monkeypatch.setattr(squads_service.client_hub_repo, "write_audit", lambda *_args, **_kwargs: None)

    result = squads_service.run_squad(
        workspace_id,
        RunSquadPayload(
            pilar="onboarding",
            squad_slug="client-onboarding",
            squad_name="Onboarding",
            input_data={"company_name": "Cliente"},
        ),
        eg_admin,
    )

    assert result.generation_mode == "preview"
    assert result.output_data["initial_deliverables"] == ["Reunião de kickoff"]
