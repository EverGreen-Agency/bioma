"""Leitura manual do DataForSEO para snapshots internos de SEO.

Este módulo só consulta o endpoint Live. Ele não cria tarefas persistentes,
não agenda coletas e não altera configuração alguma no DataForSEO.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


ENDPOINT = "/v3/dataforseo_labs/google/domain_rank_overview/live"


class DataForSeoError(RuntimeError):
    pass


def normalize_domain_rank_response(payload: dict[str, Any], target: str) -> dict[str, Any]:
    if payload.get("status_code") != 20000:
        raise DataForSeoError(
            f"DataForSEO recusou a consulta: {payload.get('status_code')} {payload.get('status_message', '')}".strip()
        )
    tasks = payload.get("tasks") or []
    if len(tasks) != 1:
        raise DataForSeoError("DataForSEO não retornou a única tarefa esperada.")
    task = tasks[0]
    if task.get("status_code") != 20000:
        raise DataForSeoError(
            f"Tarefa DataForSEO falhou: {task.get('status_code')} {task.get('status_message', '')}".strip()
        )
    results = task.get("result") or []
    items = results[0].get("items") if results else []
    item = items[0] if items else None
    metrics = (item or {}).get("metrics") or {}
    organic = metrics.get("organic") or {}
    paid = metrics.get("paid") or {}
    return {
        "source": "dataforseo",
        "source_endpoint": ENDPOINT,
        "source_task_id": task.get("id"),
        "target": target,
        "location_code": (item or {}).get("location_code") or (results[0].get("location_code") if results else 2076),
        "language_code": (item or {}).get("language_code") or (results[0].get("language_code") if results else "pt"),
        "has_data": item is not None,
        "organic": organic,
        "paid": paid,
        "cost_usd": task.get("cost") if task.get("cost") is not None else payload.get("cost"),
        "measured_at": datetime.now(timezone.utc),
        "raw_response": payload,
    }


def collect_domain_rank_snapshot(target: str, settings) -> dict[str, Any]:
    login = settings.dataforseo_login
    password = settings.dataforseo_password
    if not login or not password:
        raise DataForSeoError(
            "DataForSEO não configurado. Defina DATAFORSEO_LOGIN e DATAFORSEO_PASSWORD no runtime do worker."
        )
    normalized_target = target.removeprefix("https://").removeprefix("http://").removeprefix("www.").strip("/")
    try:
        response = httpx.post(
            f"{settings.dataforseo_base_url.rstrip('/')}{ENDPOINT}",
            auth=(login, password),
            headers={"Content-Type": "application/json"},
            json=[{
                "target": normalized_target,
                "location_code": 2076,
                "language_code": "pt",
                "limit": 1,
                "tag": "bioma-manual-seo-snapshot",
            }],
            timeout=settings.dataforseo_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise DataForSeoError(f"DataForSEO respondeu HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise DataForSeoError(f"Falha ao consultar DataForSEO: {exc}") from exc
    return normalize_domain_rank_response(payload, normalized_target)
