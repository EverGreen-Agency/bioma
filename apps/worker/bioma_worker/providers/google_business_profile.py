from datetime import date
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from bioma_worker.google_client import GoogleApiClient
from bioma_worker.storage import resolve_workspace_id, upsert_rows

SCOPE = ("https://www.googleapis.com/auth/business.manage",)

# Métricas diárias documentadas da Business Profile Performance API — soma-se
# desktop+mobile pra dar um número único de "impressões" por canal (mapas vs busca).
DAILY_METRICS = (
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
    "WEBSITE_CLICKS",
    "CALL_CLICKS",
    "BUSINESS_DIRECTION_REQUESTS",
)


def sync(
    conn,
    client: GoogleApiClient,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    location = connection["external_account_id"].removeprefix("locations/")
    params = [("dailyMetrics", metric) for metric in DAILY_METRICS]
    params += [
        ("dailyRange.start_date.year", date_from.year),
        ("dailyRange.start_date.month", date_from.month),
        ("dailyRange.start_date.day", date_from.day),
        ("dailyRange.end_date.year", date_to.year),
        ("dailyRange.end_date.month", date_to.month),
        ("dailyRange.end_date.day", date_to.day),
    ]
    endpoint = (
        f"https://businessprofileperformance.googleapis.com/v1/locations/{location}"
        f":fetchMultiDailyMetricsTimeSeries?{urlencode(params)}"
    )
    response = client.request_json("GET", endpoint, SCOPE)
    workspace_id = resolve_workspace_id(conn, client_id)

    by_date: dict[str, dict[str, int]] = {}
    for series in response.get("multiDailyMetricTimeSeries", []):
        for metric_series in series.get("dailyMetricTimeSeries", []):
            metric_name = metric_series.get("dailyMetric")
            for point in (metric_series.get("timeSeries") or {}).get("datedValues", []):
                point_date = point.get("date") or {}
                if not all(k in point_date for k in ("year", "month", "day")):
                    continue
                key = f"{point_date['year']:04d}-{point_date['month']:02d}-{point_date['day']:02d}"
                by_date.setdefault(key, {})[metric_name] = int(point.get("value", 0) or 0)

    rows = [_row(workspace_id, client_id, location, day, metrics) for day, metrics in by_date.items()]
    return upsert_rows(
        conn,
        "workspace_business_profile_daily_metrics",
        (
            "workspace_id", "client_id", "date", "location_id", "impressions_maps", "impressions_search",
            "website_clicks", "call_clicks", "direction_requests",
        ),
        ("workspace_id", "location_id", "date"),
        rows,
    )


def _row(workspace_id: UUID, client_id: UUID, location: str, day: str, metrics: dict[str, int]) -> dict[str, Any]:
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "date": day,
        "location_id": location,
        "impressions_maps": metrics.get("BUSINESS_IMPRESSIONS_DESKTOP_MAPS", 0) + metrics.get("BUSINESS_IMPRESSIONS_MOBILE_MAPS", 0),
        "impressions_search": metrics.get("BUSINESS_IMPRESSIONS_DESKTOP_SEARCH", 0) + metrics.get("BUSINESS_IMPRESSIONS_MOBILE_SEARCH", 0),
        "website_clicks": metrics.get("WEBSITE_CLICKS", 0),
        "call_clicks": metrics.get("CALL_CLICKS", 0),
        "direction_requests": metrics.get("BUSINESS_DIRECTION_REQUESTS", 0),
    }
