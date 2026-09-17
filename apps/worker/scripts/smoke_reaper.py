"""Smoke do reaper de fila (QUEUE-001).

Exercita `storage.reclaim_stalled_jobs` contra Postgres real: um job preso
em `running` com lease vencido e tentativa disponível volta para `queued`;
sem tentativa, vira `error` com `JOB_STALLED`; um job com heartbeat recente
não é tocado. Cobre tanto `sync_runs` quanto `ai_content_requests`.

Requer banco isolado (sufixo _test/_smoke), como os demais smokes mutáveis:
    BIOMA_SMOKE_DATABASE_URL=postgresql://.../bioma_smoke python scripts/smoke_reaper.py
"""

import os
from pathlib import Path
import sys
from urllib.parse import urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SMOKE_DATABASE_URL = os.environ.get("BIOMA_SMOKE_DATABASE_URL")
if not SMOKE_DATABASE_URL:
    raise RuntimeError("Defina BIOMA_SMOKE_DATABASE_URL para executar smoke_reaper.py fora do banco operacional.")
smoke_database_name = urlparse(SMOKE_DATABASE_URL).path.lstrip("/").lower()
if not smoke_database_name.endswith(("_test", "_smoke")):
    raise RuntimeError("BIOMA_SMOKE_DATABASE_URL deve apontar para um banco com sufixo _test ou _smoke.")
os.environ["DATABASE_URL"] = SMOKE_DATABASE_URL

from bioma_worker.db import connect
from bioma_worker import storage

# Lease curto e limite baixo para o teste; independem do default de produção.
LEASE_SECONDS = 60
MAX_ATTEMPTS = 3


def _setup(conn, suffix: str):
    tenant = conn.execute(
        "select id from organizations where type = 'eg' order by created_at asc limit 1"
    ).fetchone()
    if not tenant:
        raise AssertionError("seed precisa criar a organização EG antes do smoke do reaper")
    organization_id = conn.execute(
        """
        insert into organizations (name, slug, type, parent_organization_id)
        values (%s, %s, 'client', %s)
        returning id
        """,
        (f"Reaper Smoke {suffix}", f"reaper-smoke-{suffix}", tenant["id"]),
    ).fetchone()["id"]
    client_id = conn.execute(
        """
        insert into clients (organization_id, name, status)
        values (%s, %s, 'onboarding')
        returning id
        """,
        (organization_id, f"Reaper Smoke {suffix}"),
    ).fetchone()["id"]
    workspace_id = conn.execute(
        """
        insert into workspaces (
          tenant_organization_id, subject_organization_id, kind, name, slug
        )
        values (%s, %s, 'client', %s, %s)
        returning id
        """,
        (tenant["id"], organization_id, f"Reaper Smoke {suffix}", f"reaper-smoke-{suffix}"),
    ).fetchone()["id"]
    return organization_id, client_id, workspace_id


def _insert_sync(conn, organization_id, client_id, *, stale: bool, attempts: int) -> str:
    # heartbeat no passado = lease vencido; recente = job ainda vivo.
    heartbeat = "now() - interval '1 hour'" if stale else "now()"
    return conn.execute(
        f"""
        insert into sync_runs (
          source, organization_id, client_id, provider, status,
          heartbeat_at, attempts, summary
        )
        values ('performance', %s, %s, 'ga4', 'running', {heartbeat}, %s, '{{}}'::jsonb)
        returning id
        """,
        (organization_id, client_id, attempts),
    ).fetchone()["id"]


def _insert_ai(conn, organization_id, workspace_id, *, stale: bool, attempts: int) -> str:
    heartbeat = "now() - interval '1 hour'" if stale else "now()"
    return conn.execute(
        f"""
        insert into ai_content_requests (
          workspace_id, organization_id, brief, status, heartbeat_at, attempts
        )
        values (%s, %s, 'brief de smoke', 'running', {heartbeat}, %s)
        returning id
        """,
        (workspace_id, organization_id, attempts),
    ).fetchone()["id"]


def main() -> None:
    suffix = uuid4().hex[:8]
    with connect() as conn:
        organization_id, client_id, workspace_id = _setup(conn, suffix)

        # sync: vencido com tentativa sobrando → requeue.
        sync_requeue = _insert_sync(conn, organization_id, client_id, stale=True, attempts=1)
        # sync: vencido no limite de tentativas → error.
        sync_fail = _insert_sync(conn, organization_id, client_id, stale=True, attempts=MAX_ATTEMPTS)
        # sync: heartbeat recente → intocado.
        sync_alive = _insert_sync(conn, organization_id, client_id, stale=False, attempts=1)
        # ai: os dois desfechos.
        ai_requeue = _insert_ai(conn, organization_id, workspace_id, stale=True, attempts=1)
        ai_fail = _insert_ai(conn, organization_id, workspace_id, stale=True, attempts=MAX_ATTEMPTS)

        summary = storage.reclaim_stalled_jobs(conn, LEASE_SECONDS, MAX_ATTEMPTS)

        def status_of(table: str, row_id: str) -> dict:
            return conn.execute(
                f"select status, attempts, heartbeat_at, error_code from {table} where id = %s"
                if table == "sync_runs"
                else f"select status, attempts, heartbeat_at from {table} where id = %s",
                (row_id,),
            ).fetchone()

        requeued = status_of("sync_runs", sync_requeue)
        assert requeued["status"] == "queued", requeued
        assert requeued["heartbeat_at"] is None, requeued

        failed = status_of("sync_runs", sync_fail)
        assert failed["status"] == "error", failed
        assert failed["error_code"] == "JOB_STALLED", failed

        alive = status_of("sync_runs", sync_alive)
        assert alive["status"] == "running", alive

        ai_requeued = status_of("ai_content_requests", ai_requeue)
        assert ai_requeued["status"] == "queued", ai_requeued

        ai_failed = status_of("ai_content_requests", ai_fail)
        assert ai_failed["status"] == "error", ai_failed

        # O resumo precisa contar exatamente o que foi mexido nesta rodada.
        assert summary["requeued_syncs"] >= 1
        assert summary["failed_syncs"] >= 1
        assert summary["requeued_ai_content"] >= 1
        assert summary["failed_ai_content"] >= 1

        conn.execute("delete from organizations where id = %s", (organization_id,))

    print("worker reaper smoke ok")


if __name__ == "__main__":
    main()
