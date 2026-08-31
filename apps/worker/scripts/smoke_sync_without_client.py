"""Smoke do limite conhecido: sync de workspace SEM registro de cliente.

Por que existe: a conexao de performance passou a pertencer ao workspace
(migracao 0087), mas o caminho de ESCRITA nao acompanhou — os 16 provedores
montam linhas com `client_id`, e as tabelas diarias do Google exigem
`workspace_id NOT NULL` preenchido por um trigger que resolve o workspace A
PARTIR do cliente.

Com `client_id` nulo o trigger desiste, `workspace_id` fica nulo e o insert
morre com erro de constraint — depois de a rodada ja ter chamado a API externa
e gasto cota. Este smoke fixa o comportamento que troca esse erro cru por um
motivo legivel na trilha.

Quando o caminho de escrita for migrado, ESTE SMOKE DEVE QUEBRAR. E o
lembrete de que a guarda existe para ser removida.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datetime import date, timedelta

from bioma_worker.db import connect
from bioma_worker.orchestrator import run_next_sync

SMOKE_ACCOUNT = "smoke-sem-cliente-0001"


def cleanup(conn) -> None:
    conn.execute("delete from performance_connections where external_account_id = %s", (SMOKE_ACCOUNT,))
    conn.execute(
        "delete from sync_runs where summary->>'skipped' is not null or error_code = 'WORKSPACE_WITHOUT_CLIENT'"
    )


def main() -> None:
    with connect() as conn:
        cleanup(conn)
        workspace = conn.execute(
            "select id, subject_organization_id from workspaces where kind = 'agency_internal' limit 1"
        ).fetchone()
        if not workspace:
            raise AssertionError("workspace da agencia nao existe — rode create_eg_client.py")

        # Conexao SEM cliente: exatamente o caso da Operacao EG depois da 0087.
        conn.execute(
            """
            insert into performance_connections (workspace_id, organization_id, provider, external_account_id, status)
            values (%s, %s, 'google_ads', %s, 'active')
            on conflict (workspace_id, provider, external_account_id) do nothing
            """,
            (workspace["id"], workspace["subject_organization_id"], SMOKE_ACCOUNT),
        )
        # Fila limpa, para o proximo job ser o nosso.
        conn.execute("delete from sync_runs where status in ('queued', 'running')")
        sync_id = conn.execute(
            """
            insert into sync_runs (source, organization_id, client_id, workspace_id, provider, status, summary, date_from, date_to)
            values ('performance', %s, null, %s, 'all', 'queued', '{}'::jsonb, %s, %s)
            returning id
            """,
            (
                workspace["subject_organization_id"],
                workspace["id"],
                date.today() - timedelta(days=1),
                date.today(),
            ),
        ).fetchone()["id"]

    try:
        result = run_next_sync()
        if not result:
            raise AssertionError("o worker nao pegou o job enfileirado")
        if result["status"] != "error":
            raise AssertionError(f"sync sem cliente deveria falhar explicitamente: {result}")
        if "client" not in result["reason"].lower():
            raise AssertionError(f"o motivo nao explica a causa: {result['reason']}")
        print("ok: sync de workspace sem cliente para com motivo legivel")

        with connect() as conn:
            row = conn.execute(
                "select status, error_code, error_message, records_processed from sync_runs where id = %s",
                (sync_id,),
            ).fetchone()
        if row["status"] != "error" or row["error_code"] != "WORKSPACE_WITHOUT_CLIENT":
            raise AssertionError(f"a trilha nao registrou o motivo: {dict(row)}")
        print("ok: a trilha do sync guarda o codigo e a mensagem do limite")

        # A guarda age ANTES de qualquer escrita: falhar depois gastaria cota
        # do provedor e poderia deixar linha pela metade.
        if row["records_processed"] != 0:
            raise AssertionError(f"a guarda deixou escrever antes de parar: {row['records_processed']}")
        print("ok: nada foi gravado — a guarda age antes da escrita")

        print("\nSMOKE SYNC WITHOUT CLIENT: OK")
    finally:
        with connect() as conn:
            cleanup(conn)
            conn.execute("delete from sync_runs where id = %s", (sync_id,))


if __name__ == "__main__":
    main()
