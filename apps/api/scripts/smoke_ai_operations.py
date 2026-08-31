"""Smoke transacional do control plane de IA.

Recusa execução fora de banco `_smoke`/`_test`. Não usa seed nem dados do
ambiente operacional.
"""

from pathlib import Path
import sys
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect  # noqa: E402
from bioma_api.repositories import ai_operations as repo  # noqa: E402
from bioma_api.services.ai_operations import WORKFLOW_TEMPLATES  # noqa: E402


def main() -> None:
    with connect() as conn:
        database_name = conn.execute("select current_database() as name").fetchone()["name"]
        if not database_name.endswith(("_smoke", "_test")):
            raise RuntimeError("Smoke recusado: DATABASE_URL deve apontar para banco _smoke ou _test.")

        suffix = uuid4().hex[:8]
        organization_id = conn.execute(
            """
            insert into organizations (name, slug, type)
            values (%s, %s, 'eg')
            returning id
            """,
            (f"EG AI Ops Smoke {suffix}", f"eg-aiops-{suffix}"),
        ).fetchone()["id"]
        user_id = conn.execute(
            """
            insert into users (email, display_name, password_hash)
            values (%s, 'AI Ops Smoke', 'not-a-login')
            returning id
            """,
            (f"aiops-{suffix}@smoke.invalid",),
        ).fetchone()["id"]
        workspace_id = conn.execute(
            """
            insert into workspaces (
              tenant_organization_id, subject_organization_id, kind, name, slug
            )
            values (%s, %s, 'agency_internal', %s, %s)
            returning id
            """,
            (organization_id, organization_id, f"AI Ops Smoke {suffix}", f"aiops-{suffix}"),
        ).fetchone()["id"]

        subscription = repo.create_subscription(
            conn,
            organization_id,
            user_id,
            {
                "provider": "smoke-provider",
                "product_name": "smoke-plan",
                "billing_mode": "hybrid",
                "billing_cycle": "annual",
                "billing_cycle_months": 12,
                "amount_cents": 12000,
                "currency": "BRL",
                "seats": 2,
                "status": "active",
            },
        )
        quota = repo.create_quota_snapshot(
            conn,
            organization_id,
            subscription["id"],
            user_id,
            {
                "total_units": 100,
                "used_units": 35,
                "unit": "requests",
                "source": "configured",
            },
        )
        assert quota

        usage_payload = {
            "workspace_id": workspace_id,
            "provider": "smoke-provider",
            "model": "smoke-model",
            "source": "smoke",
            "external_event_id": f"event-{suffix}",
            "input_units": 10,
            "output_units": 5,
            "unit": "tokens",
            "cost_cents": 7,
            "currency": "BRL",
            "metadata": {"smoke": True},
        }
        first_usage = repo.create_usage_event(conn, organization_id, user_id, usage_payload)
        second_usage = repo.create_usage_event(conn, organization_id, user_id, usage_payload)
        assert first_usage["id"] == second_usage["id"]

        definition = repo.install_definition(
            conn,
            organization_id,
            user_id,
            WORKFLOW_TEMPLATES["tech-delivery"],
        )
        definition_row = repo.get_definition(conn, organization_id, definition["id"])
        run_payload = {
            "workspace_id": workspace_id,
            "idempotency_key": f"smoke-{suffix}",
            "input": {"contract_scope": "Escopo de smoke sem dado real."},
            "estimated_cost_cents": 100,
            "currency": "BRL",
        }
        first_run = repo.create_run(conn, organization_id, user_id, definition_row, run_payload)
        repeated_run = repo.create_run(conn, organization_id, user_id, definition_row, run_payload)
        assert first_run["id"] == repeated_run["id"]

        while True:
            run = repo.get_run(conn, organization_id, first_run["id"])
            if run["status"] == "completed":
                break
            if run["status"] == "pending_approval":
                assert repo.approve_run(conn, organization_id, run["id"], user_id)
                run = repo.get_run(conn, organization_id, run["id"])
            assert repo.complete_step(
                conn,
                organization_id,
                run["id"],
                run["current_step_key"],
                {"output": {"smoke": True}, "currency": "BRL", "cost_cents": 0},
            )

        final_run = repo.get_run(conn, organization_id, first_run["id"])
        steps = repo.list_run_steps(conn, [first_run["id"]])
        assert final_run["status"] == "completed"
        assert all(step["status"] == "completed" for step in steps)

    print("smoke_ai_operations: ok")


if __name__ == "__main__":
    main()
