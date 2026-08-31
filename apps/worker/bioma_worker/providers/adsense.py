from datetime import date
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from bioma_worker.google_client import GoogleApiClient
from bioma_worker.storage import resolve_workspace_id, upsert_rows

SCOPE = ("https://www.googleapis.com/auth/adsense.readonly",)
METRICS = ("ESTIMATED_EARNINGS", "PAGE_VIEWS", "CLICKS", "TOTAL_IMPRESSIONS")


def sync(
    conn,
    client: GoogleApiClient,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    account = connection["external_account_id"].removeprefix("accounts/")
    params = [("metrics", metric) for metric in METRICS]
    params += [
        ("dimensions", "DATE"),
        ("dateRange", "CUSTOM"),
        ("startDate.year", date_from.year), ("startDate.month", date_from.month), ("startDate.day", date_from.day),
        ("endDate.year", date_to.year), ("endDate.month", date_to.month), ("endDate.day", date_to.day),
    ]
    endpoint = f"https://adsense.googleapis.com/v2/accounts/{account}/reports:generate?{urlencode(params)}"
    response = client.request_json("GET", endpoint, SCOPE)
    workspace_id = resolve_workspace_id(conn, client_id)

    header_names = [(h or {}).get("name") for h in response.get("headers", [])]
    rows = []
    for report_row in response.get("rows", []):
        cell_values = [(c or {}).get("value") for c in report_row.get("cells", [])]
        values = dict(zip(header_names, cell_values))
        report_date = values.get("DATE")
        if not report_date:
            continue
        rows.append({
            "workspace_id": workspace_id,
            "client_id": client_id,
            "date": report_date,
            "account_id": account,
            "estimated_earnings_cents": round(float(values.get("ESTIMATED_EARNINGS") or 0) * 100),
            "page_views": int(values.get("PAGE_VIEWS") or 0),
            "clicks": int(values.get("CLICKS") or 0),
            "impressions": int(values.get("TOTAL_IMPRESSIONS") or 0),
        })

    return upsert_rows(
        conn,
        "workspace_adsense_daily_metrics",
        ("workspace_id", "client_id", "date", "account_id", "estimated_earnings_cents", "page_views", "clicks", "impressions"),
        ("workspace_id", "account_id", "date"),
        rows,
    )
