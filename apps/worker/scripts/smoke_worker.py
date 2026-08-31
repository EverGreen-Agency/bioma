from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_worker.providers.ga4 import _normalize_report
from bioma_worker.providers.google_ads import _campaign_row
from bioma_worker.providers.gtm import audit_tags


CLIENT_ID = UUID("11111111-1111-1111-1111-111111111111")


def main() -> None:
    healthy = audit_tags(
        [
            {"name": "Google Tag", "type": "googtag", "firingTriggerId": ["2147479553"]},
            {"name": "Conversion Linker", "type": "gclidw", "firingTriggerId": ["2147479553"]},
        ]
    )
    assert [finding["code"] for finding in healthy] == ["STATUS_HEALTHY"]

    unhealthy = audit_tags([{"name": "Tag órfã", "type": "html"}])
    assert {finding["code"] for finding in unhealthy} == {
        "MISSING_GA4_CONFIG",
        "MISSING_CONVERSION_LINKER",
        "ORPHAN_TAGS",
    }

    ga4_rows = _normalize_report(
        CLIENT_ID,
        {
            "dimensionHeaders": [{"name": "date"}, {"name": "sessionSource"}],
            "metricHeaders": [{"name": "sessions"}],
            "rows": [
                {
                    "dimensionValues": [{"value": "20260710"}, {"value": "google"}],
                    "metricValues": [{"value": "42"}],
                }
            ],
        },
        {"sessionSource": "source"},
    )
    assert ga4_rows[0]["date"] == "2026-07-10"
    assert ga4_rows[0]["source"] == "google"
    assert ga4_rows[0]["sessions"] == 42

    campaign = _campaign_row(
        CLIENT_ID,
        "1234567890",
        {
            "segments": {"date": "2026-07-10"},
            "campaign": {
                "id": "99",
                "name": "Pesquisa",
                "status": "ENABLED",
                "advertisingChannelType": "SEARCH",
            },
            "campaignBudget": {"amountMicros": "1000000"},
            "metrics": {
                "impressions": "100",
                "clicks": "7",
                "costMicros": "500000",
                "conversions": 2.5,
                "allConversions": 3,
                "conversionValue": 120,
            },
        },
    )
    assert campaign["clicks"] == 7
    assert campaign["budget_micros"] == 1_000_000
    assert campaign["all_conversions"] == 3

    print("worker smoke ok")


if __name__ == "__main__":
    main()
