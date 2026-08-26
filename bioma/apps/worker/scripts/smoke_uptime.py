"""Smoke do coletor de disponibilidade, contra o Postgres real.

Não usa a conta do Better Stack: a resposta HTTP é substituída por uma fixa. O
que se testa aqui é o NOSSO comportamento, e ele precisa valer sem depender de
um terceiro estar no ar — inclusive porque o coletor existe justamente para o
caso em que as coisas caem.

Valida:
- sem token, o coletor devolve `skipped` com o motivo e NÃO grava nada. Um
  painel de confiabilidade que preenche buraco com estimativa destrói o que
  existe para construir;
- com resposta do provedor, grava uma linha por janela, com os campos certos;
- rodar duas vezes no mesmo dia ATUALIZA em vez de duplicar (a chave única é
  provider+monitor+dia+janela) — cron que roda duas vezes não pode virar duas
  barras no gráfico;
- `measured_since` é preservado, que é o campo que impede "100% em 90 dias"
  num monitor de um dia parecer resultado;
- falha de um monitor não derruba a rodada dos outros;
- sem URL de heartbeat, o ping é `skipped` e não quebra o worker.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone

from bioma_worker import uptime as collector
from bioma_worker.db import connect

SMOKE_MONITOR = "smoke-uptime-000001"
BROKEN_MONITOR = "smoke-uptime-broken"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    """Cliente HTTP falso. `fail_for` simula um monitor que o provedor recusa —
    o coletor precisa seguir para os outros em vez de abortar a rodada."""

    def __init__(self, fail_for: str | None = None):
        self.fail_for = fail_for

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, headers=None, params=None, timeout=None):
        if url.endswith("/monitors"):
            data = [
                {
                    "id": SMOKE_MONITOR,
                    "attributes": {
                        "pronounceable_name": "Smoke Uptime",
                        "created_at": "2026-05-01T00:00:00.000Z",
                    },
                }
            ]
            if self.fail_for:
                data.append(
                    {"id": BROKEN_MONITOR, "attributes": {"pronounceable_name": "Smoke Quebrado"}}
                )
            return FakeResponse({"data": data})
        if url.endswith("/heartbeats"):
            return FakeResponse({"data": []})
        if self.fail_for and f"/{self.fail_for}/sla" in url:
            import httpx

            raise httpx.HTTPError("provedor recusou")
        return FakeResponse(
            {
                "data": {
                    "attributes": {
                        "availability": 99.987,
                        "total_downtime": 120,
                        "number_of_incidents": 2,
                        "longest_incident": 90,
                        "average_incident": 60,
                    }
                }
            }
        )


def cleanup() -> None:
    with connect() as conn:
        conn.execute(
            "delete from uptime_snapshots where monitor_id = any(%s)",
            ([SMOKE_MONITOR, BROKEN_MONITOR],),
        )


def rows_for(monitor_id: str):
    with connect() as conn:
        return conn.execute(
            """
            select window_days, availability, number_of_incidents, total_downtime_seconds, measured_since
            from uptime_snapshots
            where monitor_id = %s and snapshot_date = %s
            order by window_days
            """,
            # UTC, o MESMO relogio do coletor (`datetime.now(timezone.utc)`).
            # Com `date.today()` local, este smoke falhava todo dia entre 21h e
            # meia-noite no Brasil: o coletor gravava sob a data de amanha em UTC
            # e a leitura procurava sob a de hoje. Teste que passa 21 horas por
            # dia e pior que teste que falha — ele ensina a ignorar a falha.
            (monitor_id, datetime.now(timezone.utc).date()),
        ).fetchall()


def main() -> None:
    original_client = collector.httpx.Client
    original_settings = collector.get_settings
    cleanup()

    class Settings:
        betterstack_api_token = None
        betterstack_heartbeat_url = None

    try:
        # ---------------------------------------------------------------- 1
        collector.get_settings = lambda: Settings()
        result = collector.collect_uptime()
        if result["status"] != "skipped" or "BETTERSTACK_API_TOKEN" not in result["reason"]:
            raise AssertionError(f"sem token deveria pular com motivo: {result}")
        if rows_for(SMOKE_MONITOR):
            raise AssertionError("coletor gravou dado sem token — inventou medicao")
        print("ok: sem token nao inventa medicao, e diz por que pulou")

        beat = collector.ping_heartbeat()
        if beat["status"] != "skipped":
            raise AssertionError(f"sem URL o heartbeat deveria pular: {beat}")
        print("ok: heartbeat sem URL pula sem quebrar o worker")

        # ---------------------------------------------------------------- 2
        Settings.betterstack_api_token = "token-de-smoke"
        collector.httpx.Client = lambda *a, **k: FakeClient()
        result = collector.collect_uptime()
        if result["status"] != "ok" or result["snapshots"] != len(collector.WINDOWS):
            raise AssertionError(f"coleta nao gravou as janelas esperadas: {result}")

        rows = rows_for(SMOKE_MONITOR)
        if [row["window_days"] for row in rows] != sorted(collector.WINDOWS):
            raise AssertionError(f"janelas gravadas erradas: {rows}")
        if float(rows[0]["availability"]) != 99.987:
            raise AssertionError(f"disponibilidade nao foi preservada: {rows[0]}")
        if rows[0]["number_of_incidents"] != 2 or rows[0]["total_downtime_seconds"] != 120:
            raise AssertionError(f"campos do incidente perdidos: {rows[0]}")
        if str(rows[0]["measured_since"]) != "2026-05-01":
            raise AssertionError(f"measured_since perdido: {rows[0]}")
        print(f"ok: {len(rows)} janelas gravadas com incidentes e measured_since")

        # ---------------------------------------------------------------- 3
        collector.collect_uptime()
        rows = rows_for(SMOKE_MONITOR)
        if len(rows) != len(collector.WINDOWS):
            raise AssertionError(f"rodar duas vezes duplicou linhas: {len(rows)}")
        print("ok: rodar duas vezes no mesmo dia atualiza, nao duplica")

        # ---------------------------------------------------------------- 4
        collector.httpx.Client = lambda *a, **k: FakeClient(fail_for=BROKEN_MONITOR)
        result = collector.collect_uptime()
        if result["status"] != "ok":
            raise AssertionError(f"um monitor com falha derrubou a rodada: {result}")
        if rows_for(BROKEN_MONITOR):
            raise AssertionError("monitor que falhou gravou dado mesmo assim")
        if len(rows_for(SMOKE_MONITOR)) != len(collector.WINDOWS):
            raise AssertionError("monitor sadio deixou de ser coletado por causa do quebrado")
        print("ok: falha de um monitor nao derruba a coleta dos outros")

        print("\nSMOKE UPTIME: OK")
    finally:
        collector.httpx.Client = original_client
        collector.get_settings = original_settings
        cleanup()


if __name__ == "__main__":
    main()
