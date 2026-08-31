from datetime import date, datetime
from typing import Any
from uuid import UUID

from bioma_worker.google_client import GoogleApiClient
from bioma_worker.storage import upsert_rows


SCOPE = ("https://www.googleapis.com/auth/analytics.readonly",)


REPORTS = (
    {
        "table": "ga4_acquisition_daily",
        "dimensions": ("date", "sessionSource", "sessionMedium", "sessionCampaignName"),
        "metrics": (
            "sessions", "totalUsers", "newUsers", "engagedSessions",
            "engagementRate", "keyEvents",
        ),
        "columns": (
            "client_id", "date", "source", "medium", "campaign", "sessions",
            "total_users", "new_users", "engaged_sessions", "engagement_rate", "key_events",
        ),
        "conflict": ("client_id", "date", "source", "medium", "campaign"),
        "mapping": {
            "sessionSource": "source",
            "sessionMedium": "medium",
            "sessionCampaignName": "campaign",
            "totalUsers": "total_users",
            "newUsers": "new_users",
            "engagedSessions": "engaged_sessions",
            "engagementRate": "engagement_rate",
            "keyEvents": "key_events",
        },
    },
    {
        "table": "ga4_landing_page_daily",
        "dimensions": ("date", "landingPagePlusQueryString"),
        "metrics": (
            "sessions", "totalUsers", "engagedSessions", "engagementRate",
            "averageSessionDuration", "screenPageViews", "keyEvents",
        ),
        "columns": (
            "client_id", "date", "landing_page", "sessions", "total_users",
            "engaged_sessions", "engagement_rate", "average_session_duration",
            "screen_page_views", "key_events",
        ),
        "conflict": ("client_id", "date", "landing_page"),
        "mapping": {
            "landingPagePlusQueryString": "landing_page",
            "totalUsers": "total_users",
            "engagedSessions": "engaged_sessions",
            "engagementRate": "engagement_rate",
            "averageSessionDuration": "average_session_duration",
            "screenPageViews": "screen_page_views",
            "keyEvents": "key_events",
        },
    },
    {
        "table": "ga4_event_daily",
        "dimensions": ("date", "eventName"),
        "metrics": ("eventCount", "totalUsers", "keyEvents"),
        "columns": ("client_id", "date", "event_name", "event_count", "total_users", "key_events"),
        "conflict": ("client_id", "date", "event_name"),
        "mapping": {
            "eventName": "event_name",
            "eventCount": "event_count",
            "totalUsers": "total_users",
            "keyEvents": "key_events",
        },
    },
    {
        "table": "ga4_device_daily",
        "dimensions": ("date", "deviceCategory"),
        "metrics": ("sessions", "totalUsers", "engagedSessions", "keyEvents"),
        "columns": (
            "client_id", "date", "device_category", "sessions", "total_users",
            "engaged_sessions", "key_events",
        ),
        "conflict": ("client_id", "date", "device_category"),
        "mapping": {
            "deviceCategory": "device_category",
            "totalUsers": "total_users",
            "engagedSessions": "engaged_sessions",
            "keyEvents": "key_events",
        },
    },
)


def sync(
    conn,
    client: GoogleApiClient,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    property_name = connection["external_account_id"]
    if not property_name.startswith("properties/"):
        property_name = f"properties/{property_name}"
    endpoint = f"https://analyticsdata.googleapis.com/v1beta/{property_name}:runReport"
    total = 0

    for report in REPORTS:
        response = client.request_json(
            "POST",
            endpoint,
            SCOPE,
            json_body={
                "dateRanges": [{"startDate": date_from.isoformat(), "endDate": date_to.isoformat()}],
                "dimensions": [{"name": name} for name in report["dimensions"]],
                "metrics": [{"name": name} for name in report["metrics"]],
                "limit": "100000",
            },
        )
        rows = _normalize_report(client_id, response, report["mapping"])
        total += upsert_rows(
            conn,
            report["table"],
            report["columns"],
            report["conflict"],
            rows,
        )
    return total


def _normalize_report(
    client_id: UUID,
    response: dict[str, Any],
    mapping: dict[str, str],
) -> list[dict[str, Any]]:
    dimensions = [item["name"] for item in response.get("dimensionHeaders", [])]
    metrics = [item["name"] for item in response.get("metricHeaders", [])]
    normalized: list[dict[str, Any]] = []
    for raw_row in response.get("rows", []):
        row: dict[str, Any] = {"client_id": client_id}
        for name, value in zip(dimensions, raw_row.get("dimensionValues", []), strict=False):
            target = mapping.get(name, name)
            row[target] = _normalize_date(value.get("value", "")) if name == "date" else value.get("value", "")
        for name, value in zip(metrics, raw_row.get("metricValues", []), strict=False):
            target = mapping.get(name, _snake_case(name))
            row[target] = _metric(value.get("value"))
        normalized.append(row)
    return normalized


def _normalize_date(value: str) -> str:
    if len(value) == 8 and value.isdigit():
        return datetime.strptime(value, "%Y%m%d").date().isoformat()
    return value


def _metric(value: str | None) -> int | float:
    if not value:
        return 0
    number = float(value)
    return int(number) if number.is_integer() else number


def _snake_case(value: str) -> str:
    output = []
    for character in value:
        if character.isupper():
            output.append("_")
            output.append(character.lower())
        else:
            output.append(character)
    return "".join(output).lstrip("_")
