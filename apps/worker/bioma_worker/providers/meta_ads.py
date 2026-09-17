from datetime import date
from typing import Any
from uuid import UUID

import httpx

from bioma_worker.storage import resolve_workspace_id, upsert_rows

# Action types cujo somatório contamos como "lead" ou "conversion" — a Graph
# API não tem uma métrica universal de conversão, cada conta usa os action
# types que configurou nos próprios eventos/pixel.
LEAD_ACTION_TOKENS = ("lead",)
CONVERSION_ACTION_TOKENS = ("purchase", "offsite_conversion", "onsite_conversion")


def sync(
    conn,
    client: httpx.Client,
    settings,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    access_token = settings.meta_ads_access_token
    if not access_token:
        raise RuntimeError("META_ADS_ACCESS_TOKEN não configurado no worker.")

    account_id = connection["external_account_id"].removeprefix("act_")
    endpoint = f"https://graph.facebook.com/{settings.meta_ads_api_version}/act_{account_id}/insights"
    params = {
        "access_token": access_token,
        "level": "campaign",
        "time_increment": "1",
        "time_range": f'{{"since":"{date_from.isoformat()}","until":"{date_to.isoformat()}"}}',
        "fields": "campaign_id,campaign_name,date_start,impressions,clicks,spend,actions,action_values",
        "limit": "500",
    }

    rows = _fetch_insights(client, endpoint, params)
    workspace_id = resolve_workspace_id(conn, client_id)
    account_name = connection.get("metadata", {}).get("account_name") or connection["external_account_id"]

    return upsert_rows(
        conn,
        "workspace_meta_ads_daily_metrics",
        (
            "workspace_id", "client_id", "date", "account_id", "account_name",
            "campaign_id", "campaign_name", "impressions", "clicks", "spend_cents",
            "conversions", "leads", "revenue_cents",
        ),
        ("workspace_id", "campaign_id", "date"),
        [_row(workspace_id, client_id, account_id, account_name, item) for item in rows],
    )


def _fetch_insights(client: httpx.Client, endpoint: str, params: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    url: str | None = endpoint
    request_params: dict[str, str] | None = params
    while url:
        response = client.get(url, params=request_params)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(f"Meta Graph API: {payload['error'].get('message', payload['error'])}")
        rows.extend(payload.get("data", []))
        next_url = payload.get("paging", {}).get("next")
        url = next_url
        request_params = None  # next já vem com todos os query params embutidos
    return rows


def _row(workspace_id: UUID, client_id: UUID, account_id: str, account_name: str, item: dict[str, Any]) -> dict[str, Any]:
    actions = item.get("actions") or []
    action_values = item.get("action_values") or []
    leads = sum(_number(a.get("value")) for a in actions if _matches(a.get("action_type"), LEAD_ACTION_TOKENS))
    conversions = sum(_number(a.get("value")) for a in actions if _matches(a.get("action_type"), CONVERSION_ACTION_TOKENS))
    revenue = sum(_number(a.get("value")) for a in action_values if _matches(a.get("action_type"), CONVERSION_ACTION_TOKENS))
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "date": item.get("date_start"),
        "account_id": account_id,
        "account_name": account_name,
        "campaign_id": item.get("campaign_id"),
        "campaign_name": item.get("campaign_name"),
        "impressions": int(_number(item.get("impressions"))),
        "clicks": int(_number(item.get("clicks"))),
        "spend_cents": round(_number(item.get("spend")) * 100),
        "conversions": int(conversions),
        "leads": int(leads),
        "revenue_cents": round(revenue * 100),
    }


def _matches(action_type: str | None, tokens: tuple[str, ...]) -> bool:
    value = (action_type or "").lower()
    return any(token in value for token in tokens)


def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)
