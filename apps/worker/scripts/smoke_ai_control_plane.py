from pathlib import Path
import os
import sys

WORKER_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = WORKER_ROOT.parent / "api"
sys.path.insert(0, str(WORKER_ROOT))
sys.path.insert(0, str(API_ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_worker import orchestrator


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"
ACCOUNT_NAME = "SMOKE Codex control plane"
IDEMPOTENCY_KEY = "smoke-ai-control-plane-video-script-v1"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def cleanup() -> None:
    with connect() as conn:
        conn.execute(
            "delete from ai_workflow_runs where idempotency_key = %s",
            (IDEMPOTENCY_KEY,),
        )
        account_ids = [
            row["id"]
            for row in conn.execute(
                "select id from ai_provider_accounts where display_name = %s",
                (ACCOUNT_NAME,),
            ).fetchall()
        ]
        if account_ids:
            run_ids = [
                row["workflow_run_id"]
                for row in conn.execute(
                    """
                    select distinct workflow_run_id
                    from ai_execution_attempts
                    where account_id = any(%s) and workflow_run_id is not null
                    """,
                    (account_ids,),
                ).fetchall()
            ]
            if run_ids:
                conn.execute("delete from ai_workflow_runs where id = any(%s)", (run_ids,))
            conn.execute("delete from ai_provider_accounts where id = any(%s)", (account_ids,))


def fake_execute(candidate, job, settings):
    return {
        "text": f"Entrega smoke da etapa {job['step_key']} via {candidate['channel']}/{candidate['model_id']}.",
        "usage": {"input_units": 100, "output_units": 40, "cached_units": 10},
        "cost_cents": None,
        "currency": "USD",
        "latency_ms": 12,
        "external_event_id": f"smoke-{job['run_id']}-{job['step_key']}",
        "metadata": {"smoke": True},
    }


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if "_smoke" not in database_url and "_test" not in database_url:
        raise RuntimeError("Smoke recusado: DATABASE_URL deve apontar para banco _smoke ou _test.")
    cleanup()
    client = TestClient(app)
    login = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    assert_status(login, 200, "login")
    original_executor = orchestrator.execute_candidate
    orchestrator.execute_candidate = fake_execute
    try:
        account_response = client.post(
            "/backoffice/ai-operations/accounts",
            json={
                "provider": "openai",
                "channel": "codex_chatgpt",
                "display_name": ACCOUNT_NAME,
                "auth_mode": "chatgpt",
                "execution_mode": "local_cli",
                "capabilities": ["chat", "content", "strategy", "code"],
                "settings": {},
            },
        )
        assert_status(account_response, 201, "create provider account")
        account = next(row for row in account_response.json()["accounts"] if row["display_name"] == ACCOUNT_NAME)
        account_id = account["id"]

        assert_status(
            client.post(f"/backoffice/ai-operations/accounts/{account_id}/models/bootstrap"),
            200,
            "bootstrap models",
        )
        assert_status(
            client.post(
                f"/backoffice/ai-operations/accounts/{account_id}/quota-buckets",
                json={
                    "bucket_key": "weekly",
                    "scope": "account",
                    "remaining_percent": 90,
                    "unit": "percent",
                    "window_duration_minutes": 10080,
                    "source": "configured",
                    "confidence": "manual",
                    "notes": "fixture smoke",
                },
            ),
            201,
            "record quota",
        )
        assert_status(
            client.post("/backoffice/ai-operations/routing-policies/bootstrap"),
            200,
            "bootstrap policies",
        )
        preview = client.post(
            "/backoffice/ai-operations/route-preview",
            json={"task_kind": "content_draft"},
        )
        assert_status(preview, 200, "route preview")
        assert preview.json()["selected"]["account_id"] == account_id

        definitions = client.post("/backoffice/ai-operations/workflow-templates/video-script/install")
        assert_status(definitions, 200, "install workflow")
        definition = next(row for row in definitions.json() if row["slug"] == "video-script" and row["version"] == 1)
        run_response = client.post(
            "/backoffice/ai-operations/workflow-runs",
            json={
                "definition_id": definition["id"],
                "idempotency_key": IDEMPOTENCY_KEY,
                "input": {"brief": "Roteiro smoke para validar o control plane ponta a ponta."},
                "currency": "USD",
            },
        )
        assert_status(run_response, 202, "create workflow run")
        run_id = run_response.json()["id"]
        assert run_response.json()["status"] == "pending_approval"
        assert_status(
            client.post(f"/backoffice/ai-operations/workflow-runs/{run_id}/approve"),
            200,
            "approve workflow start",
        )

        first = orchestrator.run_next_ai_workflow()
        assert first and first["step"] == "angle" and first["status"] == "waiting_approval"
        checkpoint = client.get("/backoffice/ai-operations/workflow-runs").json()
        current = next(row for row in checkpoint if row["id"] == run_id)
        assert current["status"] == "pending_approval"
        assert current["steps"][0]["output"]["text"].startswith("Entrega smoke")
        assert current["steps"][0]["model"]

        assert_status(
            client.post(f"/backoffice/ai-operations/workflow-runs/{run_id}/approve"),
            200,
            "approve angle",
        )
        second = orchestrator.run_next_ai_workflow()
        assert second and second["step"] == "script" and second["status"] == "completed"
        third = orchestrator.run_next_ai_workflow()
        assert third and third["step"] == "review" and third["status"] == "waiting_approval"
        completed = client.post(f"/backoffice/ai-operations/workflow-runs/{run_id}/approve")
        assert_status(completed, 200, "approve review")
        assert completed.json()["status"] == "completed"
        assert all(step["status"] == "completed" for step in completed.json()["steps"])

        quota_job = client.post(f"/backoffice/ai-operations/accounts/{account_id}/quota-collection")
        assert_status(quota_job, 202, "enqueue Codex quota collection")
        job = next(row for row in quota_job.json()["quota_collection_jobs"] if row["account_id"] == account_id)
        assert job["status"] == "queued"
    finally:
        orchestrator.execute_candidate = original_executor
        cleanup()
    print("smoke_ai_control_plane: ok")


if __name__ == "__main__":
    main()
