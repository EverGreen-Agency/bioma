from datetime import date, datetime
from typing import Any
from uuid import UUID

import httpx

from bioma_worker.crypto import decrypt_secret
from bioma_worker.storage import resolve_workspace_id, upsert_rows

BASE_URL = "https://crm.rdstation.com/api/v1"
PAGE_LIMIT = 200


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
        raise RuntimeError("SECRET_ENCRYPTION_KEY não configurado no worker — necessário pra decifrar o token do RD Station.")

    metadata = connection.get("metadata") or {}
    encrypted = metadata.get("api_token")
    if not encrypted:
        raise RuntimeError("Conexão RD Station CRM sem token salvo — configure o token em Integrações.")
    token = decrypt_secret(encrypted, settings.secret_encryption_key)

    deals = _list_deals(client, token, date_from, date_to)
    workspace_id = resolve_workspace_id(conn, client_id)

    rows = [_row(workspace_id, client_id, deal) for deal in deals]
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


def _list_deals(client: httpx.Client, token: str, date_from: date, date_to: date) -> list[dict[str, Any]]:
    deals: list[dict[str, Any]] = []
    page = 1
    while True:
        response = client.get(
            f"{BASE_URL}/deals",
            params={
                "token": token,
                "page": page,
                "limit": PAGE_LIMIT,
                "created_at_period": "true",
                "start_date": date_from.isoformat(),
                "end_date": date_to.isoformat(),
            },
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("errors"):
            raise RuntimeError(f"RD Station CRM: {payload['errors']}")

        batch = payload.get("deals", []) if isinstance(payload, dict) else payload
        if not batch:
            break
        deals.extend(batch)
        if len(batch) < PAGE_LIMIT:
            break
        page += 1
        # Limite documentado da API: 10.000 registros por consulta de listagem.
        if len(deals) >= 10_000:
            break
    return deals


def _row(workspace_id: UUID, client_id: UUID, deal: dict[str, Any]) -> dict[str, Any]:
    # `win` é true (ganho), false (perdido) ou null (em aberto).
    win = deal.get("win")
    status = "won" if win is True else "lost" if win is False else "open"

    stage = deal.get("deal_stage") or {}
    user = deal.get("user") or {}
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "source": "rd_station_crm",
        "external_deal_id": str(deal.get("id")),
        "name": deal.get("name"),
        "amount_cents": round(_number(deal.get("amount_total") or deal.get("amount_unique")) * 100),
        "currency": "BRL",
        "stage": stage.get("name") if isinstance(stage, dict) else None,
        "pipeline": (deal.get("deal_pipeline") or {}).get("name") if isinstance(deal.get("deal_pipeline"), dict) else None,
        "status": status,
        "owner_name": user.get("name") if isinstance(user, dict) else None,
        "external_created_at": _timestamp(deal.get("created_at")),
        "external_closed_at": _timestamp(deal.get("closed_at")),
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
