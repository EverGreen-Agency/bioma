from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException

from bioma_api.schemas.client_profile import ClientProfilePayload
from bioma_api.services import client_profiles as service


def test_profile_completion_is_computed_from_real_fields(eg_admin, monkeypatch):
    workspace_id = uuid4()

    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(
        service,
        "resolve_accessible_client",
        lambda *_args, **_kwargs: {"workspace_id": workspace_id, "workspace_kind": "client", "organization_id": uuid4()},
    )
    monkeypatch.setattr(
        service.profile_repo,
        "get_profile",
        lambda *_args: {"sector": "Saúde", "primary_offer": "Clínica", "initial_objective": "Mais leads", "updated_at": None},
    )

    profile = service.get_profile(workspace_id, eg_admin)

    assert profile.completion_percentage == 19
    assert profile.sections[0].filled == 3
    assert profile.sections[0].percentage == 100


def test_profile_write_requires_manage_work_and_is_audited(eg_admin, monkeypatch):
    workspace_id = uuid4()
    organization_id = uuid4()
    calls = []
    audits = []

    @contextmanager
    def fake_connect():
        yield object()

    def fake_workspace(_conn, _workspace_id, _user, *, capability, **_kwargs):
        calls.append(capability)
        return {"workspace_id": workspace_id, "workspace_kind": "client", "organization_id": organization_id}

    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(service, "resolve_accessible_client", fake_workspace)
    monkeypatch.setattr(
        service.profile_repo,
        "upsert_profile",
        lambda *_args: {"sector": "Energia", "updated_at": None},
    )
    monkeypatch.setattr(
        service.client_hub_repo,
        "write_audit",
        lambda *_args: audits.append(_args[3]),
    )

    result = service.upsert_profile(workspace_id, ClientProfilePayload(sector=" Energia "), eg_admin)

    assert calls == ["manage_work"]
    assert result.sector == "Energia"
    assert audits == ["client_profile.updated"]


def test_empty_profile_update_is_rejected(eg_admin):
    with pytest.raises(HTTPException) as exc:
        service.upsert_profile(uuid4(), ClientProfilePayload(), eg_admin)

    assert exc.value.status_code == 422
