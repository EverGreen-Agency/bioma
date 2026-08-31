from datetime import date, datetime
from typing import Any
from uuid import UUID

import httpx

from bioma_worker.crypto import decrypt_secret
from bioma_worker.storage import resolve_workspace_id, upsert_rows

DEALS_URL = "https://api.hubapi.com/crm/v3/objects/deals"
PIPELINES_URL = "https://api.hubapi.com/crm/v3/pipelines/deals"
PAGE_LIMIT = 100
PROPERTIES = "dealname,amount,dealstage,pipeline,closedate,createdate,hs_deal_stage_probability"


def sync(
    conn,
    client: httpx.Client,
    settings,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    if not settings.secret_encryption_key:
        raise RuntimeError("SECRET_ENCRYPTION_KEY não configurado no worker — necessário pra decifrar o token do HubSpot.")

    metadata = connection.get("metadata") or {}
    encrypted = metadata.get("api_token")
    if not encrypted:
        raise RuntimeError("Conexão HubSpot sem token salvo — configure o token do app privado em Integrações.")
    token = decrypt_secret(encrypted, settings.secret_encryption_key)
    headers = {"Authorization": f"Bearer {token}"}

    # O HubSpot devolve dealstage/pipeline como IDs internos; buscamos o mapa de
    # rótulos pra gravar nome legível em vez de hash opaco.
    stage_labels, pipeline_labels, closed_won, closed_lost = _pipeline_metadata(client, headers)

    deals = _list_deals(client, headers)
    workspace_id = resolve_workspace_id(conn, client_id)

    rows = [
        _row(workspace_id, client_id, deal, stage_labels, pipeline_labels, closed_won, closed_lost)
        for deal in deals
    ]
    return upsert_rows(
        conn,
        "workspace_crm_deals",
        (
            "workspace_id", "client_id", "source", "external_deal_id", "name", "amount_cents",
            "currency", "stage", "pipeline", "status", "owner_name",
            "external_created_at", "external_closed_at",
        ),
        ("workspace_id", "source", "external_deal_id"),
        rows,
    )


def _pipeline_metadata(
    client: httpx.Client, headers: dict[str, str]
) -> tuple[dict[str, str], dict[str, str], set[str], set[str]]:
    response = client.get(PIPELINES_URL, headers=headers)
    response.raise_for_status()
    payload = response.json()

    stage_labels: dict[str, str] = {}
    pipeline_labels: dict[str, str] = {}
    closed_won: set[str] = set()
    closed_lost: set[str] = set()

    for pipeline in payload.get("results", []):
        pipeline_labels[pipeline["id"]] = pipeline.get("label", pipeline["id"])
        for stage in pipeline.get("stages", []):
            stage_labels[stage["id"]] = stage.get("label", stage["id"])
            stage_metadata = stage.get("metadata") or {}
            # HubSpot marca o desfecho da etapa em metadata.isClosed + probability
            # (1 = ganho, 0 = perdido). É o único jeito confiável de saber o
            # status sem chutar pelo nome da etapa, que cada conta personaliza.
            if str(stage_metadata.get("isClosed")).lower() == "true":
                probability = str(stage_metadata.get("probability", ""))
                if probability in ("1", "1.0"):
                    closed_won.add(stage["id"])
                elif probability in ("0", "0.0"):
                    closed_lost.add(stage["id"])

    return stage_labels, pipeline_labels, closed_won, closed_lost


def _list_deals(client: httpx.Client, headers: dict[str, str]) -> list[dict[str, Any]]:
    deals: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        params: dict[str, Any] = {"limit": PAGE_LIMIT, "properties": PROPERTIES}
        if after:
            params["after"] = after
        response = client.get(DEALS_URL, headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()

        deals.extend(payload.get("results", []))
        after = ((payload.get("paging") or {}).get("next") or {}).get("after")
        if not after:
            break
    return deals


def _row(
    workspace_id: UUID,
    client_id: UUID,
    deal: dict[str, Any],
    stage_labels: dict[str, str],
    pipeline_labels: dict[str, str],
    closed_won: set[str],
    closed_lost: set[str],
) -> dict[str, Any]:
    properties = deal.get("properties") or {}
    stage_id = properties.get("dealstage") or ""
    pipeline_id = properties.get("pipeline") or ""

    status = "won" if stage_id in closed_won else "lost" if stage_id in closed_lost else "open"

    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "source": "hubspot",
        "external_deal_id": str(deal.get("id")),
        "name": properties.get("dealname"),
        "amount_cents": round(_number(properties.get("amount")) * 100),
        "currency": "BRL",
        "stage": stage_labels.get(stage_id, stage_id or None),
        "pipeline": pipeline_labels.get(pipeline_id, pipeline_id or None),
        "status": status,
        "owner_name": None,
        "external_created_at": _timestamp(properties.get("createdate")),
        "external_closed_at": _timestamp(properties.get("closedate")),
    }


def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
