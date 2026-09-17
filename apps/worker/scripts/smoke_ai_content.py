from pathlib import Path
import json
import os
import sys

WORKER_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = WORKER_ROOT.parent / "api"
sys.path.insert(0, str(WORKER_ROOT))
sys.path.insert(0, str(API_ROOT))

import httpx
from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_worker.ai_content import generate_content
from bioma_worker.config import WorkerSettings, get_settings
from bioma_worker.orchestrator import run_next_ai_content


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "henrique@hmconexoes.com.br"
PASSWORD = "senha-dev-123"
BRIEF = "SMOKE AI: divulgar uma nova consultoria estratégica para conexões de negócio."


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert_status(response, 200, f"login {email}")


def cleanup() -> None:
    with connect() as conn:
        ids = [row["id"] for row in conn.execute(
            "select id from ai_content_requests where brief = %s",
            (BRIEF,),
        ).fetchall()]
        if ids:
            conn.execute("delete from ai_runs where content_request_id = any(%s)", (ids,))
            conn.execute("delete from ai_content_requests where id = any(%s)", (ids,))


def main() -> None:
    cleanup()
    os.environ.pop("OPENAI_API_KEY", None)
    get_settings.cache_clear()
    admin = TestClient(app)
    client_user = TestClient(app)
    login(admin, ADMIN_EMAIL)
    login(client_user, CLIENT_EMAIL)

    try:
        workspaces = admin.get("/workspaces")
        assert_status(workspaces, 200, "list workspaces")
        hm = next(row for row in workspaces.json() if row["organization_slug"] == "hm-conexoes")
        internal = next(row for row in workspaces.json() if row["kind"] == "agency_internal")

        created = client_user.post(
            f"/workspaces/{hm['id']}/ai/content",
            json={
                "brief": BRIEF,
                "channels": ["instagram", "linkedin"],
                "quantity": 3,
                "tone": "consultivo e direto",
                "objective": "gerar conversas qualificadas",
                "methodology_refs": ["Social Media Engine", "Conexões Poderosas"],
            },
        )
        assert_status(created, 202, "client requests content")
        request_id = created.json()["id"]
        assert created.json()["status"] == "queued"
        assert_status(
            client_user.get(f"/workspaces/{internal['id']}/ai/content"),
            404,
            "AI request isolation",
        )

        result = run_next_ai_content()
        assert result and result["id"] == request_id
        assert result["status"] == "ready"
        assert result["generation_mode"] == "preview"

        listed = client_user.get(f"/workspaces/{hm['id']}/ai/content")
        assert_status(listed, 200, "list generated content")
        generated = next(row for row in listed.json() if row["id"] == request_id)
        assert generated["provider"] == "local_preview"
        assert len(generated["output"]["posts"]) == 3

        with connect() as conn:
            run = conn.execute(
                "select status, provider, workspace_id from ai_runs where content_request_id = %s",
                (request_id,),
            ).fetchone()
        assert run["status"] == "ok" and run["provider"] == "local_preview"
        assert str(run["workspace_id"]) == hm["id"]

        _smoke_openai_adapter()
    finally:
        cleanup()
        get_settings.cache_clear()

    print("ai content smoke ok")


def _smoke_openai_adapter() -> None:
    output = {
        "strategy_note": "Estratégia mockada",
        "posts": [
            {
                "title": f"Post {index + 1}",
                "channel": channel,
                "format": "carrossel",
                "hook": "Hook",
                "caption": "Legenda",
                "cta": "CTA",
            }
            for index, channel in enumerate(["instagram", "linkedin", "instagram"])
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-5.6-sol"
        assert payload["text"]["format"]["type"] == "json_schema"
        assert payload["text"]["format"]["strict"] is True
        return httpx.Response(
            200,
            json={
                "id": "resp_smoke",
                "model": "gpt-5.6-sol",
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}
                ],
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            },
        )

    settings = WorkerSettings(openai_api_key="test-key", openai_model="gpt-5.6-sol")
    request = {
        "brief": BRIEF,
        "channels": ["instagram", "linkedin"],
        "quantity": 3,
        "tone": "consultivo",
        "objective": "conversas",
        "methodology_refs": [],
    }
    with httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.openai.com") as client:
        result = generate_content(request, settings, http_client=client)
    assert result["provider"] == "openai"
    assert result["generation_mode"] == "live"
    assert len(result["output"]["posts"]) == 3


if __name__ == "__main__":
    main()
