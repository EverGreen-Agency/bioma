from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID
from urllib.parse import quote

import httpx

from bioma_worker.crypto import decrypt_secret
from bioma_worker.storage import resolve_workspace_id, upsert_rows

STATS_URL = "https://api.linkedin.com/rest/organizationalEntityShareStatistics"
LINKEDIN_API_VERSION = "202506"


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
        raise RuntimeError("SECRET_ENCRYPTION_KEY não configurado no worker — necessário pra decifrar o token do LinkedIn.")

    metadata = connection.get("metadata") or {}
    encrypted_access = metadata.get("oauth_access_token")
    if not encrypted_access:
        raise RuntimeError("Conexão LinkedIn sem token OAuth salvo — refaça a autorização em Integrações.")
    access_token = decrypt_secret(encrypted_access, settings.secret_encryption_key)

    organization_urn = connection["external_account_id"]
    start_ms = int(datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(date_to, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)

    time_intervals = f"(timeRange:(start:{start_ms},end:{end_ms}),timeGranularityType:DAY)"
    url = (
        f"{STATS_URL}?q=organizationalEntity"
        f"&organizationalEntity={quote(organization_urn, safe='')}"
        f"&timeIntervals={quote(time_intervals, safe='(),:')}"
    )
    response = client.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Linkedin-Version": LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    response.raise_for_status()
    payload = response.json()
    if "message" in payload and "status" in payload:
        raise RuntimeError(f"LinkedIn: {payload.get('message')}")

    workspace_id = resolve_workspace_id(conn, client_id)
    elements = payload.get("elements") or []
    rows = [_row(workspace_id, client_id, organization_urn, item) for item in elements if item.get("timeRange")]
    return upsert_rows(
        conn,
        "workspace_linkedin_organic_daily_metrics",
        (
            "workspace_id", "client_id", "date", "organization_urn", "impressions", "unique_impressions",
            "clicks", "likes", "comments", "shares",
        ),
        ("workspace_id", "organization_urn", "date"),
        rows,
    )


def _row(workspace_id: UUID, client_id: UUID, organization_urn: str, item: dict[str, Any]) -> dict[str, Any]:
    time_range = item.get("timeRange") or {}
    stats = item.get("totalShareStatistics") or {}
    start_ms = time_range.get("start")
    day = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).date() if start_ms else None
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "date": day,
        "organization_urn": organization_urn,
        "impressions": int(stats.get("impressionCount") or 0),
        "unique_impressions": int(stats.get("uniqueImpressionsCount") or 0),
        "clicks": int(stats.get("clickCount") or 0),
        "likes": int(stats.get("likeCount") or 0),
        "comments": int(stats.get("commentCount") or 0),
        "shares": int(stats.get("shareCount") or 0),
    }
