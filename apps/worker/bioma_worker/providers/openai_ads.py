from datetime import date
from typing import Any
from uuid import UUID

import httpx

from bioma_worker.storage import resolve_workspace_id, upsert_rows


def sync(
    conn,
    client: httpx.Client,
    settings,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    access_token = getattr(settings, "openai_ads_api_key", None) or connection.get("metadata", {}).get("api_key")
    if not access_token:
        return 0

    account_id = connection["external_account_id"]
    endpoint = f"https://ads.openai.com/v1/accounts/{account_id}/reports"
    params = {
        "start_date": date_from.isoformat(),
        "end_date": date_to.isoformat(),
        "group_by": "campaign,date",
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        res = client.get(endpoint, headers=headers, params=params)
        res.raise_for_status()
        data = res.json().get("data", [])
    except Exception:
        data = []

    workspace_id = resolve_workspace_id(conn, client_id)
    account_name = connection.get("metadata", {}).get("account_name") or account_id

    rows = []
    for item in data:
        rows.append((
            workspace_id,
            client_id,
            item.get("date", date_from.isoformat()),
            account_id,
            account_name,
            item.get("campaign_id", "default"),
            item.get("campaign_name", "Campanha ChatGPT"),
            item.get("impressions", 0),
            item.get("clicks", 0),
            int(item.get("spend", 0) * 100),
            item.get("conversions", 0),
        ))

    return upsert_rows(
        conn,
        "workspace_openai_ads_daily_metrics",
        (
            "workspace_id", "client_id", "date", "account_id", "account_name",
            "campaign_id", "campaign_name", "impressions", "clicks", "spend_cents",
            "conversions",
        ),
        ("workspace_id", "campaign_id", "date"),
        rows,
    )
