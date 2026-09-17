import json
from pathlib import Path
import sys

import httpx


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.integrations.github import GitHubClient


def main() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        assert request.headers["Authorization"] == "Bearer test-token"
        if request.url.path.endswith("/issues"):
            return httpx.Response(200, json=[
                {
                    "number": 12, "title": "Corrigir autenticação", "state": "open",
                    "html_url": "https://github.test/eg/app/issues/12", "labels": [{"name": "bug"}],
                    "updated_at": "2026-07-23T10:00:00Z",
                },
                {
                    "number": 13, "title": "PR misturado na API de issues", "state": "open",
                    "html_url": "https://github.test/eg/app/pull/13", "labels": [],
                    "updated_at": "2026-07-23T11:00:00Z", "pull_request": {},
                },
            ])
        if request.url.path.endswith("/pulls"):
            return httpx.Response(200, json=[{
                "number": 13, "title": "Fase 3", "state": "open", "draft": False,
                "html_url": "https://github.test/eg/app/pull/13",
                "head": {"ref": "feat/fase-3"}, "base": {"ref": "main"},
                "updated_at": "2026-07-23T11:00:00Z",
            }])
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=[{
                "sha": "abc123", "html_url": "https://github.test/eg/app/commit/abc123",
                "commit": {"message": "feat: fase 3\n\nDetalhes", "author": {"name": "Eduardo", "date": "2026-07-23T09:00:00Z"}},
            }])
        return httpx.Response(404, json={"message": "not found"})

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://api.github.test",
        headers={"Authorization": "Bearer test-token"},
    ) as http_client:
        client = GitHubClient("test-token", http_client=http_client)
        result = client.project_activity("eg", "app", "main", 20)

    assert len(result["issues"]) == 1
    assert result["issues"][0]["labels"] == ["bug"]
    assert result["pull_requests"][0]["source_branch"] == "feat/fase-3"
    assert result["commits"][0]["message"] == "feat: fase 3"
    assert requested_paths == [
        "/repos/eg/app/issues", "/repos/eg/app/pulls", "/repos/eg/app/commits",
    ]
    assert "test-token" not in json.dumps(result, default=str)
    print("github read smoke ok")


if __name__ == "__main__":
    main()
