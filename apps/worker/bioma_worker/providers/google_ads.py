from datetime import date
from typing import Any
from uuid import UUID

from bioma_worker.config import WorkerSettings
from bioma_worker.google_client import GoogleApiClient
from bioma_worker.storage import upsert_rows


SCOPE = ("https://www.googleapis.com/auth/adwords",)


def sync(
    conn,
    client: GoogleApiClient,
    settings: WorkerSettings,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    developer_token = settings.google_ads_developer_token
    if not developer_token:
        raise RuntimeError("GOOGLE_ADS_DEVELOPER_TOKEN não configurado no worker.")

    customer_id = _digits(connection["external_account_id"])
    login_customer_id = _digits(
        connection.get("external_parent_id") or settings.google_ads_login_customer_id or ""
    )
    headers = {"developer-token": developer_token}
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id

    endpoint = (
        f"https://googleads.googleapis.com/{settings.google_ads_api_version}/"
        f"customers/{customer_id}/googleAds:search"
    )
    start = date_from.isoformat()
    end = date_to.isoformat()
    total = 0

    campaign_rows = _search(
        client,
        endpoint,
        headers,
        f"""
        SELECT segments.date, customer.id, campaign.id, campaign.name, campaign.status,
               campaign.advertising_channel_type, campaign_budget.amount_micros,
               metrics.impressions, metrics.clicks, metrics.cost_micros,
               metrics.conversions, metrics.all_conversions, metrics.conversion_value,
               metrics.search_impression_share
        FROM campaign
        WHERE segments.date BETWEEN '{start}' AND '{end}'
        """,
    )
    campaigns = [_campaign_row(client_id, customer_id, row) for row in campaign_rows]
    total += upsert_rows(
        conn,
        "ads_campaign_daily",
        (
            "client_id", "date", "customer_id", "campaign_id", "campaign_name",
            "campaign_status", "channel_type", "budget_micros", "impressions", "clicks",
            "cost_micros", "conversions", "all_conversions", "conversion_value",
            "search_impression_share",
        ),
        ("client_id", "date", "campaign_id"),
        campaigns,
    )

    keyword_rows = _search(
        client,
        endpoint,
        headers,
        f"""
        SELECT segments.date, campaign.id, campaign.name, ad_group.id, ad_group.name,
               ad_group_criterion.criterion_id, ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type, ad_group_criterion.status,
               metrics.impressions, metrics.clicks, metrics.cost_micros,
               metrics.conversions, metrics.conversion_value
        FROM keyword_view
        WHERE segments.date BETWEEN '{start}' AND '{end}'
          AND ad_group_criterion.status IN ('ENABLED', 'PAUSED')
        """,
    )
    total += upsert_rows(
        conn,
        "ads_keyword_daily",
        (
            "client_id", "date", "campaign_id", "campaign_name", "ad_group_id",
            "ad_group_name", "criterion_id", "keyword_text", "match_type", "status",
            "impressions", "clicks", "cost_micros", "conversions", "conversion_value",
        ),
        ("client_id", "date", "criterion_id"),
        [_keyword_row(client_id, row) for row in keyword_rows],
    )

    search_term_rows = _search(
        client,
        endpoint,
        headers,
        f"""
        SELECT segments.date, campaign.id, campaign.name, ad_group.id, ad_group.name,
               search_term_view.search_term, search_term_view.status,
               metrics.impressions, metrics.clicks, metrics.cost_micros,
               metrics.conversions, metrics.conversion_value
        FROM search_term_view
        WHERE segments.date BETWEEN '{start}' AND '{end}'
        """,
    )
    total += upsert_rows(
        conn,
        "ads_search_term_daily",
        (
            "client_id", "date", "campaign_id", "campaign_name", "ad_group_id",
            "ad_group_name", "search_term", "targeting_status", "impressions", "clicks",
            "cost_micros", "conversions", "conversion_value",
        ),
        ("client_id", "date", "campaign_id", "ad_group_id", "search_term"),
        [_search_term_row(client_id, row) for row in search_term_rows],
    )

    segment_rows = _search(
        client,
        endpoint,
        headers,
        f"""
        SELECT segments.date, campaign.id, segments.device, metrics.impressions,
               metrics.clicks, metrics.cost_micros, metrics.conversions,
               metrics.conversion_value
        FROM campaign
        WHERE segments.date BETWEEN '{start}' AND '{end}'
        """,
    )
    total += upsert_rows(
        conn,
        "ads_segment_daily",
        (
            "client_id", "date", "campaign_id", "segment_type", "segment_value",
            "impressions", "clicks", "cost_micros", "conversions", "conversion_value",
        ),
        ("client_id", "date", "campaign_id", "segment_type", "segment_value"),
        [_segment_row(client_id, row) for row in segment_rows],
    )

    conversion_rows = _search(
        client,
        endpoint,
        headers,
        f"""
        SELECT segments.date, segments.conversion_action, segments.conversion_action_name,
               segments.conversion_action_category, metrics.conversions,
               metrics.all_conversions, metrics.conversion_value
        FROM campaign
        WHERE segments.date BETWEEN '{start}' AND '{end}'
        """,
    )
    conversions = [
        _conversion_row(client_id, row)
        for row in conversion_rows
        if row.get("segments", {}).get("conversionAction")
    ]
    total += upsert_rows(
        conn,
        "ads_conversion_daily",
        (
            "client_id", "date", "conversion_action_id", "conversion_action_name",
            "conversion_category", "conversions", "all_conversions", "conversion_value",
            "cost_micros",
        ),
        ("client_id", "date", "conversion_action_id"),
        conversions,
    )
    return total


def _search(
    client: GoogleApiClient,
    endpoint: str,
    headers: dict[str, str],
    query: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        body: dict[str, Any] = {"query": " ".join(query.split()), "pageSize": 10000}
        if page_token:
            body["pageToken"] = page_token
        response = client.request_json("POST", endpoint, SCOPE, json_body=body, headers=headers)
        rows.extend(response.get("results", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return rows


def _campaign_row(client_id: UUID, customer_id: str, row: dict[str, Any]) -> dict[str, Any]:
    campaign = row["campaign"]
    metrics = row.get("metrics", {})
    return {
        "client_id": client_id,
        "date": row["segments"]["date"],
        "customer_id": customer_id,
        "campaign_id": campaign["id"],
        "campaign_name": campaign["name"],
        "campaign_status": campaign["status"],
        "channel_type": campaign.get("advertisingChannelType", "UNKNOWN"),
        "budget_micros": _number(row.get("campaignBudget", {}).get("amountMicros"), int, None),
        # A API omite impression share quando nao ha leilao elegivel no periodo;
        # nesse caso a coluna fica null (ausencia real), nao 0.
        "search_impression_share": _number(metrics.get("searchImpressionShare"), float, None),
        **_metrics(metrics, include_all=True),
    }


def _keyword_row(client_id: UUID, row: dict[str, Any]) -> dict[str, Any]:
    criterion = row["adGroupCriterion"]
    return {
        "client_id": client_id,
        "date": row["segments"]["date"],
        "campaign_id": row["campaign"]["id"],
        "campaign_name": row["campaign"]["name"],
        "ad_group_id": row["adGroup"]["id"],
        "ad_group_name": row["adGroup"]["name"],
        "criterion_id": criterion["criterionId"],
        "keyword_text": criterion["keyword"]["text"],
        "match_type": criterion["keyword"]["matchType"],
        "status": criterion["status"],
        **_metrics(row.get("metrics", {})),
    }


def _search_term_row(client_id: UUID, row: dict[str, Any]) -> dict[str, Any]:
    search_term = row["searchTermView"]
    return {
        "client_id": client_id,
        "date": row["segments"]["date"],
        "campaign_id": row["campaign"]["id"],
        "campaign_name": row["campaign"]["name"],
        "ad_group_id": row["adGroup"]["id"],
        "ad_group_name": row["adGroup"]["name"],
        "search_term": search_term["searchTerm"],
        "targeting_status": search_term.get("status"),
        **_metrics(row.get("metrics", {})),
    }


def _segment_row(client_id: UUID, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": client_id,
        "date": row["segments"]["date"],
        "campaign_id": row["campaign"]["id"],
        "segment_type": "device",
        "segment_value": row["segments"].get("device", "UNKNOWN"),
        **_metrics(row.get("metrics", {})),
    }


def _conversion_row(client_id: UUID, row: dict[str, Any]) -> dict[str, Any]:
    segments = row["segments"]
    action = segments["conversionAction"]
    metrics = row.get("metrics", {})
    return {
        "client_id": client_id,
        "date": segments["date"],
        "conversion_action_id": action.rsplit("/", 1)[-1],
        "conversion_action_name": segments.get("conversionActionName", "Unknown"),
        "conversion_category": segments.get("conversionActionCategory", "DEFAULT"),
        "conversions": _number(metrics.get("conversions"), float, 0),
        "all_conversions": _number(metrics.get("allConversions"), float, 0),
        "conversion_value": _number(metrics.get("conversionValue"), float, 0),
        "cost_micros": None,
    }


def _metrics(metrics: dict[str, Any], include_all: bool = False) -> dict[str, Any]:
    values = {
        "impressions": _number(metrics.get("impressions"), int, 0),
        "clicks": _number(metrics.get("clicks"), int, 0),
        "cost_micros": _number(metrics.get("costMicros"), int, 0),
        "conversions": _number(metrics.get("conversions"), float, 0),
        "conversion_value": _number(metrics.get("conversionValue"), float, 0),
    }
    if include_all:
        values["all_conversions"] = _number(metrics.get("allConversions"), float, 0)
    return values


def _number(value: Any, cast, default):
    if value is None or value == "":
        return default
    return cast(value)


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())
