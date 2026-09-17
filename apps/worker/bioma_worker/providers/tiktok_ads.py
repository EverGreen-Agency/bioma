from datetime import date
from typing import Any
from uuid import UUID

import httpx

from bioma_worker.crypto import decrypt_secret
from bioma_worker.storage import resolve_workspace_id, upsert_rows

REPORT_URL = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"


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
        raise RuntimeError("SECRET_ENCRYPTION_KEY não configurado no worker — necessário pra decifrar o token do TikTok Ads.")

    metadata = connection.get("metadata") or {}
    encrypted_access = metadata.get("oauth_access_token")
    if not encrypted_access:
        raise RuntimeError("Conexão TikTok Ads sem token OAuth salvo — refaça a autorização em Integrações.")
    access_token = decrypt_secret(encrypted_access, settings.secret_encryption_key)

    advertiser_id = connection["external_account_id"]
    params = {
        "advertiser_id": advertiser_id,
        "report_type": "BASIC",
        "data_level": "AUCTION_CAMPAIGN",
        "dimensions": '["campaign_id","stat_time_day"]',
        "metrics": '["campaign_name","spend","impressions","clicks","conversion"]',
        "start_date": date_from.isoformat(),
        "end_date": date_to.isoformat(),
        "page_size": 1000,
    }
    response = client.get(REPORT_URL, params=params, headers={"Access-Token": access_token})
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (0, None):
        raise RuntimeError(f"TikTok Ads: {payload.get('message', 'erro desconhecido')}")

    workspace_id = resolve_workspace_id(conn, client_id)
    items = ((payload.get("data") or {}).get("list")) or []
    rows = [_row(workspace_id, client_id, advertiser_id, item) for item in items]
    return upsert_rows(
        conn,
        "workspace_tiktok_ads_daily_metrics",
        ("workspace_id", "client_id", "date", "advertiser_id", "campaign_id", "campaign_name", "impressions", "clicks", "spend_cents", "conversions"),
        ("workspace_id", "advertiser_id", "campaign_id", "date"),
        rows,
    )


def _row(workspace_id: UUID, client_id: UUID, advertiser_id: str, item: dict[str, Any]) -> dict[str, Any]:
    dimensions = item.get("dimensions") or {}
    metrics = item.get("metrics") or {}
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "date": dimensions.get("stat_time_day", "")[:10] or None,
        "advertiser_id": advertiser_id,
        "campaign_id": dimensions.get("campaign_id"),
        "campaign_name": metrics.get("campaign_name"),
        "impressions": int(float(metrics.get("impressions") or 0)),
        "clicks": int(float(metrics.get("clicks") or 0)),
        "spend_cents": round(float(metrics.get("spend") or 0) * 100),
        "conversions": int(float(metrics.get("conversion") or 0)),
    }
