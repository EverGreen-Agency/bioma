from datetime import date
from typing import Any
from urllib.parse import quote
from uuid import UUID

from bioma_worker.google_client import GoogleApiClient
from bioma_worker.storage import upsert_rows


SCOPE = ("https://www.googleapis.com/auth/webmasters.readonly",)


def sync(
    conn,
    client: GoogleApiClient,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    site_url = connection["external_account_id"]
    endpoint = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        f"{quote(site_url, safe='')}/searchAnalytics/query"
    )
    total = 0

    query_response = _query(client, endpoint, date_from, date_to, ("date", "query", "country", "device"))
    total += upsert_rows(
        conn,
        "gsc_query_daily",
        ("client_id", "date", "query", "country", "device", "clicks", "impressions", "ctr", "position"),
        ("client_id", "date", "query", "country", "device"),
        [_row(client_id, item, "query") for item in query_response.get("rows", [])],
    )

    page_response = _query(client, endpoint, date_from, date_to, ("date", "page", "country", "device"))
    total += upsert_rows(
        conn,
        "gsc_page_daily",
        ("client_id", "date", "page", "country", "device", "clicks", "impressions", "ctr", "position"),
        ("client_id", "date", "page", "country", "device"),
        [_row(client_id, item, "page") for item in page_response.get("rows", [])],
    )
    return total


def _query(
    client: GoogleApiClient,
    endpoint: str,
    date_from: date,
    date_to: date,
    dimensions: tuple[str, ...],
) -> dict[str, Any]:
    return client.request_json(
        "POST",
        endpoint,
        SCOPE,
        json_body={
            "startDate": date_from.isoformat(),
            "endDate": date_to.isoformat(),
            "dimensions": list(dimensions),
            "rowLimit": 25000,
        },
    )


def _row(client_id: UUID, item: dict[str, Any], dimension: str) -> dict[str, Any]:
    keys = item.get("keys", [])
    return {
        "client_id": client_id,
        "date": keys[0],
        dimension: keys[1],
        "country": keys[2] if len(keys) > 2 else "unknown",
        "device": keys[3] if len(keys) > 3 else "unknown",
        "clicks": item.get("clicks", 0),
        "impressions": item.get("impressions", 0),
        "ctr": item.get("ctr", 0),
        "position": item.get("position", 0),
    }
