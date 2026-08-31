import argparse
from datetime import date, timedelta
import json

from bioma_worker.db import connect
from bioma_worker.orchestrator import reclaim_stalled_jobs, run_next_job
from bioma_worker.storage import enqueue_scheduled_syncs
from bioma_worker.uptime import collect_uptime, ping_heartbeat


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker de performance do Bioma")
    parser.add_argument("--drain", action="store_true", help="Processa a fila até ficar vazia")
    parser.add_argument("--enqueue-all", action="store_true", help="Enfileira clientes ativos antes de processar")
    parser.add_argument("--days", type=int, default=3, help="Janela incremental para --enqueue-all")
    parser.add_argument(
        "--collect-uptime",
        action="store_true",
        help="Coleta a disponibilidade medida pelo prober externo antes de processar",
    )
    parser.add_argument(
        "--skip-reaper",
        action="store_true",
        help="Não recupera jobs presos em running antes de processar (diagnóstico)",
    )
    args = parser.parse_args()

    # Antes de enfileirar: um sync preso em `running` bloqueia o
    # reenfileiramento daquele cliente em `enqueue_scheduled_syncs`.
    if not args.skip_reaper:
        reclaimed = reclaim_stalled_jobs()
        if any(reclaimed.values()):
            print(json.dumps({"reaper": reclaimed}))

    # Antes da fila: a coleta é leitura de API externa e não depende de job
    # nenhum. Rodar junto evita um segundo cron só para isso.
    if args.collect_uptime:
        print(json.dumps({"uptime": collect_uptime()}, ensure_ascii=False))

    if args.enqueue_all:
        date_to = date.today()
        date_from = date_to - timedelta(days=max(args.days, 1))
        with connect() as conn:
            queued = enqueue_scheduled_syncs(conn, date_from, date_to)
        print(json.dumps({"queued": queued, "date_from": str(date_from), "date_to": str(date_to)}))

    processed = 0
    while True:
        result = run_next_job()
        if result is None:
            if processed == 0:
                print(json.dumps({"status": "idle"}))
            break
        print(json.dumps(result, ensure_ascii=False))
        processed += 1
        if not args.drain:
            break

    # Por último e sempre: bater no heartbeat significa "a rodada terminou".
    # Bater antes diria "comecei", que é outra informação e não detecta um
    # worker que morre no meio.
    beat = ping_heartbeat()
    if beat.get("status") != "skipped":
        print(json.dumps({"heartbeat": beat}, ensure_ascii=False))


if __name__ == "__main__":
    main()
