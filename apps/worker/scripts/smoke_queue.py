from datetime import date
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SMOKE_DATABASE_URL = os.environ.get("BIOMA_SMOKE_DATABASE_URL")
if not SMOKE_DATABASE_URL:
    raise RuntimeError("Defina BIOMA_SMOKE_DATABASE_URL para executar smoke_queue.py fora do banco operacional.")
smoke_database_name = urlparse(SMOKE_DATABASE_URL).path.lstrip("/").lower()
if not smoke_database_name.endswith(("_test", "_smoke")):
    raise RuntimeError("BIOMA_SMOKE_DATABASE_URL deve apontar para um banco com sufixo _test ou _smoke.")
os.environ["DATABASE_URL"] = SMOKE_DATABASE_URL

from bioma_worker.db import connect
from bioma_worker.orchestrator import run_next_sync


def main() -> None:
    suffix = uuid4().hex[:8]
    with connect() as conn:
        tenant = conn.execute(
            "select id from organizations where type = 'eg' order by created_at asc limit 1"
        ).fetchone()
        if not tenant:
            raise AssertionError("seed precisa criar a organização EG antes do smoke do worker")
        organization_id = conn.execute(
            """
            insert into organizations (name, slug, type, parent_organization_id)
            values (%s, %s, 'client', %s)
            returning id
            """,
            (f"Worker Smoke {suffix}", f"worker-smoke-{suffix}", tenant["id"]),
        ).fetchone()["id"]
        client_id = conn.execute(
            """
            insert into clients (organization_id, name, status)
            values (%s, %s, 'onboarding')
            returning id
            """,
            (organization_id, f"Worker Smoke {suffix}"),
        ).fetchone()["id"]
        conn.execute(
            """
            insert into workspaces (
              tenant_organization_id,
              subject_organization_id,
              kind,
              name,
              slug
            )
            values (%s, %s, 'client', %s, %s)
            """,
            (tenant["id"], organization_id, f"Worker Smoke {suffix}", f"worker-smoke-{suffix}"),
        )
        conn.execute(
            """
            insert into performance_connections (
              client_id, organization_id, provider, external_account_id,
              credentials_ref, status
            )
            values (%s, %s, 'ga4', 'properties/invalid-smoke',
                    'env:GOOGLE_SERVICE_ACCOUNT_JSON', 'active')
            """,
            (client_id, organization_id),
        )
        sync_id = conn.execute(
            """
            insert into sync_runs (
              source, organization_id, client_id, provider, status,
              date_from, date_to, summary
            )
            values ('performance', %s, %s, 'ga4', 'queued', %s, %s, '{}'::jsonb)
            returning id
            """,
            (organization_id, client_id, date(2026, 7, 1), date(2026, 7, 2)),
        ).fetchone()["id"]

    result = run_next_sync()
    assert result is not None
    assert result["id"] == str(sync_id)
    assert result["status"] == "error"

    with connect() as conn:
        persisted = conn.execute(
            "select status, finished_at, error_code from sync_runs where id = %s",
            (sync_id,),
        ).fetchone()
        assert persisted["status"] == "error"
        assert persisted["finished_at"] is not None
        assert persisted["error_code"] == "PROVIDER_SYNC_FAILED"
        conn.execute("delete from organizations where id = %s", (organization_id,))

    print("worker queue smoke ok")


if __name__ == "__main__":
    main()
