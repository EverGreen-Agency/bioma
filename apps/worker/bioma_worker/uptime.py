"""Coleta a disponibilidade medida por um prober EXTERNO e guarda no Bioma.

Existe porque uptime auto-medido não vale nada: se o Bioma medisse a si mesmo,
uma queda total registraria 100% — quem mede caiu junto. A medição vem do
Better Stack; este módulo só busca e arquiva.

Guardar em vez de consultar na renderização tem dois motivos, e o segundo é o
que importa a longo prazo:

1. a tela de disponibilidade não pode depender de um terceiro estar no ar;
2. o histórico passa a ser nosso — trocar de provedor não leva o passado junto.

Sem `BETTERSTACK_API_TOKEN` o coletor não inventa nada: devolve `skipped` com o
motivo. Um painel de confiabilidade que preenche buraco com estimativa é
exatamente o que ele deveria estar combatendo.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from bioma_worker.config import get_settings
from bioma_worker.db import connect

API_BASE = "https://uptime.betterstack.com/api/v2"

# Janelas coletadas por rodada. 1 alimenta a barra de dias; 30 e 90 são os
# números publicados. Pedir as três ao provedor é mais barato e mais correto que
# derivar 90 dias somando 90 leituras nossas — a conta de disponibilidade dele
# considera a duração real do incidente, não a média dos dias.
WINDOWS = (1, 30, 90)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _get(client: httpx.Client, token: str, path: str, params: dict | None = None) -> dict[str, Any]:
    response = client.get(f"{API_BASE}{path}", headers=_headers(token), params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _sla(client: httpx.Client, token: str, kind: str, monitor_id: str, days: int, today: date) -> dict[str, Any] | None:
    """Disponibilidade de UM monitor numa janela.

    Falha de um monitor não derruba a rodada: devolve None e o chamador segue.
    Um monitor recém-criado ou apagado no provedor não pode impedir a coleta
    dos outros.
    """
    resource = "monitors" if kind == "monitor" else "heartbeats"
    start = today - timedelta(days=days - 1)
    try:
        payload = _get(
            client,
            token,
            f"/{resource}/{monitor_id}/sla",
            {"from": start.isoformat(), "to": today.isoformat()},
        )
    except httpx.HTTPError:
        return None
    return payload.get("data", {}).get("attributes")


def collect_uptime() -> dict[str, Any]:
    """Busca os monitores e arquiva a disponibilidade de cada janela."""
    settings = get_settings()
    token = getattr(settings, "betterstack_api_token", None)
    if not token:
        return {"status": "skipped", "reason": "BETTERSTACK_API_TOKEN não configurado"}

    today = datetime.now(timezone.utc).date()
    collected = 0
    monitors: list[tuple[str, str, str, date | None]] = []

    with httpx.Client() as client:
        for kind, resource in (("monitor", "monitors"), ("heartbeat", "heartbeats")):
            try:
                payload = _get(client, token, f"/{resource}")
            except httpx.HTTPError as exc:
                return {"status": "error", "reason": f"falha ao listar {resource}: {exc}"}

            for item in payload.get("data", []):
                attributes = item.get("attributes", {})
                name = attributes.get("pronounceable_name") or attributes.get("name") or attributes.get("url") or item["id"]
                created = attributes.get("created_at")
                since = None
                if created:
                    try:
                        since = datetime.fromisoformat(created.replace("Z", "+00:00")).date()
                    except ValueError:
                        since = None
                monitors.append((kind, item["id"], name, since))

        with connect() as conn:
            for kind, monitor_id, name, since in monitors:
                for days in WINDOWS:
                    attributes = _sla(client, token, kind, monitor_id, days, today)
                    if attributes is None:
                        continue
                    conn.execute(
                        """
                        insert into uptime_snapshots (
                          provider, monitor_id, monitor_name, kind, snapshot_date, window_days,
                          availability, total_downtime_seconds, number_of_incidents,
                          longest_incident_seconds, average_incident_seconds, measured_since
                        )
                        values ('betterstack', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (provider, monitor_id, snapshot_date, window_days)
                        do update set
                          monitor_name = excluded.monitor_name,
                          availability = excluded.availability,
                          total_downtime_seconds = excluded.total_downtime_seconds,
                          number_of_incidents = excluded.number_of_incidents,
                          longest_incident_seconds = excluded.longest_incident_seconds,
                          average_incident_seconds = excluded.average_incident_seconds,
                          measured_since = excluded.measured_since,
                          collected_at = now()
                        """,
                        (
                            monitor_id,
                            name,
                            kind,
                            today,
                            days,
                            attributes.get("availability", 0),
                            int(attributes.get("total_downtime", 0) or 0),
                            int(attributes.get("number_of_incidents", 0) or 0),
                            int(attributes.get("longest_incident", 0) or 0),
                            int(attributes.get("average_incident", 0) or 0),
                            since,
                        ),
                    )
                    collected += 1

    return {"status": "ok", "monitors": len(monitors), "snapshots": collected}


def ping_heartbeat() -> dict[str, Any]:
    """Avisa o prober que o worker terminou uma rodada.

    Interruptor de homem morto: se o cron parar de disparar, ninguém recebe
    erro — o worker simplesmente não roda, e nada sincroniza em silêncio. Foi
    exatamente esse o buraco que a 0087 quase deixou passar. O heartbeat é a
    única coisa que transforma "parou de acontecer" em alerta.

    Falha aqui NÃO derruba o worker: não conseguir avisar que o trabalho
    terminou não desfaz o trabalho.
    """
    settings = get_settings()
    url = getattr(settings, "betterstack_heartbeat_url", None)
    if not url:
        return {"status": "skipped", "reason": "BETTERSTACK_HEARTBEAT_URL não configurado"}
    try:
        httpx.post(url, timeout=10)
        return {"status": "ok"}
    except httpx.HTTPError as exc:
        return {"status": "error", "reason": str(exc)}
