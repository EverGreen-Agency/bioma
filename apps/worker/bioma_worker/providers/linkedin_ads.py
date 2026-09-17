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
    access_token = settings.linkedin_ads_access_token
    if not access_token:
        raise RuntimeError("LINKEDIN_ADS_ACCESS_TOKEN não configurado no worker.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": settings.linkedin_ads_api_version,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    account_id = connection["external_account_id"]
    elements = _fetch_analytics(client, headers, account_id, date_from, date_to)

    campaign_urns = sorted({item["campaign"] for item in elements if item.get("campaign")})
    campaign_names = _fetch_campaign_names(client, headers, campaign_urns)

    workspace_id = resolve_workspace_id(conn, client_id)
    account_name = connection.get("metadata", {}).get("account_name") or account_id

    return upsert_rows(
        conn,
        "workspace_linkedin_ads_daily_metrics",
        (
            "workspace_id", "client_id", "date", "account_id", "account_name",
            "campaign_id", "campaign_name", "impressions", "clicks", "spend_cents",
            "conversions", "leads", "revenue_cents",
        ),
        ("workspace_id", "campaign_id", "date"),
        [_row(workspace_id, client_id, account_id, account_name, item, campaign_names) for item in elements],
    )


def _fetch_analytics(
    client: httpx.Client,
    headers: dict[str, str],
    account_id: str,
    date_from: date,
    date_to: date,
) -> list[dict[str, Any]]:
    account_urn = account_id if account_id.startswith("urn:li:") else f"urn:li:sponsoredAccount:{account_id}"
    elements: list[dict[str, Any]] = []
    start = 0
    count = 100
    while True:
        params = {
            "q": "analytics",
            "pivot": "CAMPAIGN",
            "timeGranularity": "DAILY",
            "dateRange.start.day": str(date_from.day),
            "dateRange.start.month": str(date_from.month),
            "dateRange.start.year": str(date_from.year),
            "dateRange.end.day": str(date_to.day),
            "dateRange.end.month": str(date_to.month),
            "dateRange.end.year": str(date_to.year),
            "accounts": f"List({account_urn})",
            "fields": "campaign,dateRange,impressions,clicks,costInLocalCurrency,externalWebsiteConversions",
            "start": str(start),
            "count": str(count),
        }
        response = client.get("https://api.linkedin.com/rest/adAnalytics", headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()
        page = payload.get("elements", [])
        elements.extend(page)
        if len(page) < count:
            break
        start += count
    return elements


def _fetch_campaign_names(client: httpx.Client, headers: dict[str, str], campaign_urns: list[str]) -> dict[str, str]:
    if not campaign_urns:
        return {}
    ids = ",".join(urn.rsplit(":", 1)[-1] for urn in campaign_urns)
    try:
        response = client.get(
            "https://api.linkedin.com/rest/adCampaigns",
            headers=headers,
            params={"ids": f"List({ids})"},
        )
        response.raise_for_status()
        results = response.json().get("results", {})
        return {
            f"urn:li:sponsoredCampaign:{campaign_id}": data.get("name", campaign_id)
            for campaign_id, data in results.items()
        }
    except httpx.HTTPError:
        # Resolução de nome é best-effort: sem nome, cai no ID cru (nunca falha o sync inteiro por isso).
        return {}


def _row(
    workspace_id: UUID,
    client_id: UUID,
    account_id: str,
    account_name: str,
    item: dict[str, Any],
    campaign_names: dict[str, str],
) -> dict[str, Any]:
    campaign_urn = item.get("campaign") or ""
    campaign_id = campaign_urn.rsplit(":", 1)[-1] if campaign_urn else None
    date_range = item.get("dateRange", {}).get("start", {})
    iso_date = None
    if date_range:
        iso_date = f"{date_range['year']:04d}-{date_range['month']:02d}-{date_range['day']:02d}"
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "date": iso_date,
        "account_id": account_id,
        "account_name": account_name,
        "campaign_id": campaign_id,
        "campaign_name": campaign_names.get(campaign_urn, campaign_id),
        "impressions": int(item.get("impressions") or 0),
        "clicks": int(item.get("clicks") or 0),
        "spend_cents": round(float(item.get("costInLocalCurrency") or 0) * 100),
        "conversions": int(item.get("externalWebsiteConversions") or 0),
        "leads": int(item.get("externalWebsiteConversions") or 0),
        "revenue_cents": 0,
    }
