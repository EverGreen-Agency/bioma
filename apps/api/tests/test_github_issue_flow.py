from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from bioma_api.schemas.github import (
    GitHubActivitySyncRequest,
    GitHubCommitSummary,
    GitHubProjectActivity,
    GitHubIssueCreateRequest,
)
from bioma_api.services import github as github_service


def test_github_issue_write_is_external_to_transaction_and_marked(eg_admin, monkeypatch):
    deliverable_id = uuid4()
    project_id = uuid4()
    organization_id = uuid4()
    open_connections = 0
    created = {}
    recorded = {}

    @contextmanager
    def fake_connect():
        nonlocal open_connections
        open_connections += 1
        try:
            yield object()
        finally:
            open_connections -= 1

    class FakeGitHubClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def find_issue_by_title_prefix(self, owner, repository, prefix):
            assert open_connections == 0
            assert (owner, repository) == ("eg", "produto")
            created["prefix"] = prefix
            return None

        def create_issue(self, owner, repository, title, body):
            assert open_connections == 0
            created.update(owner=owner, repository=repository, title=title, body=body)
            return {"number": 42, "url": "https://github.com/eg/produto/issues/42"}

        def close(self):
            pass

    monkeypatch.setattr(github_service, "connect", fake_connect)
    monkeypatch.setattr(
        github_service,
        "get_settings",
        lambda: SimpleNamespace(github_api_token="token", github_api_base_url="https://api.github.test"),
    )
    monkeypatch.setattr(github_service, "GitHubClient", FakeGitHubClient)
    monkeypatch.setattr(
        github_service.github_repo,
        "find_deliverable_for_issue",
        lambda *_args: {
            "id": deliverable_id,
            "title": "Implementar autenticação",
            "project_id": project_id,
            "github_issue_number": None,
            "github_issue_url": None,
            "github_issue_write_status": "idle",
            "github_issue_write_requested_at": None,
        },
    )
    monkeypatch.setattr(
        github_service,
        "_project",
        lambda *_args, **_kwargs: {
            "id": project_id,
            "project_type": "tech",
            "subject_organization_id": organization_id,
        },
    )
    monkeypatch.setattr(
        github_service.github_repo,
        "find_connection",
        lambda *_args: {
            "repository_owner": "eg",
            "repository_name": "produto",
            "status": "active",
        },
    )
    monkeypatch.setattr(github_service.github_repo, "reserve_deliverable_issue", lambda *_args: {"id": deliverable_id})
    monkeypatch.setattr(
        github_service.github_repo,
        "record_deliverable_issue",
        lambda _conn, saved_id, number, url: recorded.update(id=saved_id, number=number, url=url),
    )
    monkeypatch.setattr(github_service.github_repo, "write_audit", lambda *_args, **_kwargs: None)

    result = github_service.create_issue_from_deliverable(
        deliverable_id,
        GitHubIssueCreateRequest(confirm=True, body="Definition of Done"),
        eg_admin,
    )

    marker = f"[Bioma:{deliverable_id}]"
    assert created["prefix"] == marker
    assert created["title"].startswith(marker)
    assert marker in created["body"]
    assert recorded == {
        "id": deliverable_id,
        "number": 42,
        "url": "https://github.com/eg/produto/issues/42",
    }
    assert result.issue_number == 42


def test_github_activity_is_published_as_idempotent_project_update(eg_admin, monkeypatch):
    project_id = uuid4()
    organization_id = uuid4()
    update_id = uuid4()
    sync_id = uuid4()
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

    activity = GitHubProjectActivity(
        project_id=project_id,
        repository="eg/produto",
        default_branch="develop",
        fetched_at=datetime.now(timezone.utc),
        issues=[],
        pull_requests=[],
        commits=[
            GitHubCommitSummary(
                sha="abcdef123456",
                message="feat: avanço real",
                url="https://github.com/eg/produto/commit/abcdef",
                authored_at=datetime.now(timezone.utc),
            ),
        ],
    )

    def fake_get_activity(*_args):
        assert open_connections == 0
        return activity

    monkeypatch.setattr(github_service, "connect", fake_connect)
    monkeypatch.setattr(
        github_service,
        "_project",
        lambda *_args, **_kwargs: {
            "id": project_id,
            "project_type": "tech",
            "subject_organization_id": organization_id,
        },
    )
    monkeypatch.setattr(github_service, "get_activity", fake_get_activity)
    monkeypatch.setattr(github_service.github_repo, "find_activity_sync", lambda *_args: None)
    monkeypatch.setattr(github_service.project_repo, "lock_project", lambda *_args: None)
    monkeypatch.setattr(
        github_service.project_repo,
        "create_project_update",
        lambda _conn, _project_id, _user_id, payload: saved.update(payload) or {"id": update_id},
    )
    monkeypatch.setattr(
        github_service.github_repo,
        "create_activity_sync",
        lambda *_args: {
            "id": sync_id,
            "project_id": project_id,
            "project_update_id": update_id,
            "idempotency_key": "github-update-2026-07-28",
            "created_at": datetime.now(timezone.utc),
        },
    )
    monkeypatch.setattr(github_service.github_repo, "write_audit", lambda *_args, **_kwargs: None)

    result = github_service.publish_activity_update(
        project_id,
        GitHubActivitySyncRequest(
            confirm=True,
            idempotency_key="github-update-2026-07-28",
            client_visible=True,
        ),
        eg_admin,
    )

    assert result.project_update_id == update_id
    assert result.repository == "eg/produto"
    assert saved["client_visible"] is True
    assert "1 commits recentes" in saved["summary"]
    assert "abcdef1 feat: avanço real" in saved["detail"]
