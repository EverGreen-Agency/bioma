"""Smoke da escrita GitHub (PROJECT-GH-002): idempotência, BOLA e confirmação HITL.

Roda in-process com TestClient. O `GitHubClient` é substituído por um dublê
que nunca sai para a rede; valida que a issue só é criada uma vez mesmo com
duas chamadas (replay) e que o número de chamadas reais ao "GitHub" é 1.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import bioma_api.services.github as github_service  # noqa: E402
from bioma_api.config import get_settings  # noqa: E402
from bioma_api.main import app  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user  # noqa: E402

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
OUTSIDER_EMAIL = "smoke-github-write-outsider@bioma.example.com"
PASSWORD = "senha-dev-123"


class FakeGitHubClient:
    calls = 0

    def __init__(self, token: str, base_url: str) -> None:
        assert token == "smoke-token"

    def close(self) -> None:
        pass

    def create_issue(self, owner: str, repository: str, title: str, body: str | None) -> dict:
        FakeGitHubClient.calls += 1
        return {"number": 501, "url": f"https://github.com/{owner}/{repository}/issues/501"}


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    assert_status(client.post("/auth/login", json={"email": email, "password": PASSWORD}), 200, f"login {email}")


def main() -> None:
    cleanup_smoke_data([], [OUTSIDER_EMAIL])
    workspace = create_smoke_workspace("GithubWrite")
    outsider_id = upsert_smoke_user(OUTSIDER_EMAIL, "GitHub Write Outsider", PASSWORD)

    os.environ["GITHUB_API_TOKEN"] = "smoke-token"
    get_settings.cache_clear()
    github_service.GitHubClient = FakeGitHubClient

    admin = TestClient(app)
    outsider = TestClient(app)

    try:
        login(admin, ADMIN_EMAIL)
        login(outsider, OUTSIDER_EMAIL)

        project = admin.post(
            f"/workspaces/{workspace.workspace_id}/projects",
            json={"name": "Tech smoke GH write", "project_type": "tech", "status": "active"},
        )
        assert_status(project, 201, "create tech project")
        project_id = project.json()["id"]

        deliverable = admin.post(
            f"/projects/{project_id}/deliverables",
            json={"title": "Corrigir bug de autenticação (smoke)", "status": "planned"},
        )
        assert_status(deliverable, 201, "create deliverable")
        deliverable_id = deliverable.json()["deliverables"][-1]["id"]

        # Sem conexão GitHub configurada: 404 (não 500).
        no_connection = admin.post(f"/integrations/github/deliverables/{deliverable_id}/issue", json={"confirm": True})
        assert_status(no_connection, 404, "sem conexao github configurada")

        connection = admin.put(
            f"/integrations/github/projects/{project_id}",
            json={"repository": "evergreen-ai-os/bioma-smoke", "default_branch": "main", "status": "active"},
        )
        assert_status(connection, 200, "configurar conexao github")

        # BOLA: usuário sem acesso ao workspace não enxerga a entrega/projeto.
        bola = outsider.post(f"/integrations/github/deliverables/{deliverable_id}/issue", json={"confirm": True})
        assert_status(bola, 404, "bola: outsider nao acessa a entrega")

        # HITL: sem confirm=true, 422 (Pydantic rejeita antes mesmo de tocar o service).
        no_confirm = admin.post(f"/integrations/github/deliverables/{deliverable_id}/issue", json={})
        assert_status(no_confirm, 422, "sem confirmacao explicita")
        no_confirm_false = admin.post(f"/integrations/github/deliverables/{deliverable_id}/issue", json={"confirm": False})
        assert_status(no_confirm_false, 422, "confirm=false rejeitado")

        # Escrita real (dublê): cria a issue.
        created = admin.post(f"/integrations/github/deliverables/{deliverable_id}/issue", json={"confirm": True})
        assert_status(created, 200, "criar issue")
        body = created.json()
        assert body["issue_number"] == 501, f"numero de issue inesperado: {body}"
        assert body["repository"] == "evergreen-ai-os/bioma-smoke"
        assert FakeGitHubClient.calls == 1, f"esperava 1 chamada ao GitHub, teve {FakeGitHubClient.calls}"

        # Replay: reprocessar não cria uma segunda issue nem chama o GitHub de novo.
        replay = admin.post(f"/integrations/github/deliverables/{deliverable_id}/issue", json={"confirm": True})
        assert_status(replay, 200, "replay idempotente")
        assert replay.json()["issue_number"] == 501
        assert FakeGitHubClient.calls == 1, f"replay chamou o GitHub de novo: {FakeGitHubClient.calls} chamadas"

        print("github write smoke ok")
    finally:
        cleanup_smoke_data([workspace.organization_id], [OUTSIDER_EMAIL])
        os.environ.pop("GITHUB_API_TOKEN", None)
        get_settings.cache_clear()


if __name__ == "__main__":
    main()
