"""Smoke do BI Social (MOD-BI-SOCIAL-001): sync real de Meta Ads e LinkedIn
Ads mockado via rede (sem credencial real), falha alta sem token configurado
(nunca retorna vazio em silêncio), e persistência na mesma tabela que a API
de leitura consulta. Workspace isolado, self-clean.
"""

from pathlib import Path
from types import SimpleNamespace
import sys

api_path = Path(__file__).resolve().parent.parent
worker_path = api_path.parent / "worker"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

import httpx  # noqa: E402

from bioma_api.db import connect  # noqa: E402
from bioma_api.repositories import performance_social as perf_social_repo  # noqa: E402
from bioma_worker.providers import linkedin_ads, meta_ads  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace  # noqa: E402

DATE_FROM = __import__("datetime").date(2026, 7, 1)
DATE_TO = __import__("datetime").date(2026, 7, 2)


def meta_transport(request: httpx.Request) -> httpx.Response:
    if "page=2" in str(request.url):
        return httpx.Response(200, json={"data": [], "paging": {}})
    return httpx.Response(
        200,
        json={
            "data": [
                {
                    "campaign_id": "meta_camp_1",
                    "campaign_name": "Campanha Meta Smoke",
                    "date_start": "2026-07-01",
                    "impressions": "1000",
                    "clicks": "50",
                    "spend": "123.45",
                    "actions": [{"action_type": "lead", "value": "4"}, {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "2"}],
                    "action_values": [{"action_type": "offsite_conversion.fb_pixel_purchase", "value": "300.00"}],
                }
            ],
            "paging": {"next": str(request.url) + ("&page=2" if "page=2" not in str(request.url) else "")},
        },
    )


def linkedin_transport(request: httpx.Request) -> httpx.Response:
    if "adCampaigns" in str(request.url):
        return httpx.Response(200, json={"results": {"999888777": {"name": "Campanha LinkedIn Smoke"}}})
    return httpx.Response(
        200,
        json={
            "elements": [
                {
                    "campaign": "urn:li:sponsoredCampaign:999888777",
                    "dateRange": {"start": {"year": 2026, "month": 7, "day": 1}},
                    "impressions": 500,
                    "clicks": 20,
                    "costInLocalCurrency": "80.00",
                    "externalWebsiteConversions": 3,
                }
            ]
        },
    )


def main() -> None:
    workspace = create_smoke_workspace("PerformanceSocial")
    connection = {"external_account_id": "act_123456", "metadata": {"account_name": "Conta Meta Smoke"}}
    connection_li = {"external_account_id": "9988776", "metadata": {"account_name": "Conta LinkedIn Smoke"}}

    try:
        # Sem credencial: falha alta, nunca retorna vazio em silêncio.
        no_token_settings = SimpleNamespace(meta_ads_access_token=None)
        try:
            with connect() as conn:
                meta_ads.sync(conn, httpx.Client(), no_token_settings, workspace.client_id, connection, DATE_FROM, DATE_TO)
            raise AssertionError("deveria ter falhado sem META_ADS_ACCESS_TOKEN")
        except RuntimeError as exc:
            assert "META_ADS_ACCESS_TOKEN" in str(exc)
        print("[OK] Meta Ads sem token: falha alta (nunca silencioso)")

        no_token_settings_li = SimpleNamespace(linkedin_ads_access_token=None)
        try:
            with connect() as conn:
                linkedin_ads.sync(conn, httpx.Client(), no_token_settings_li, workspace.client_id, connection_li, DATE_FROM, DATE_TO)
            raise AssertionError("deveria ter falhado sem LINKEDIN_ADS_ACCESS_TOKEN")
        except RuntimeError as exc:
            assert "LINKEDIN_ADS_ACCESS_TOKEN" in str(exc)
        print("[OK] LinkedIn Ads sem token: falha alta (nunca silencioso)")

        # Com token (mockado): parseia a resposta real da API e persiste.
        meta_settings = SimpleNamespace(meta_ads_access_token="smoke-token", meta_ads_api_version="v21.0")
        meta_client = httpx.Client(transport=httpx.MockTransport(meta_transport))
        with connect() as conn:
            records = meta_ads.sync(conn, meta_client, meta_settings, workspace.client_id, connection, DATE_FROM, DATE_TO)
        assert records == 1, records

        with connect() as conn:
            rows = perf_social_repo.list_meta_ads_daily(conn, workspace.workspace_id)
        assert len(rows) == 1
        assert rows[0]["campaign_name"] == "Campanha Meta Smoke"
        assert rows[0]["spend_cents"] == 12345, rows[0]
        assert rows[0]["leads"] == 4
        assert rows[0]["conversions"] == 2
        assert rows[0]["revenue_cents"] == 30000
        print("[OK] Meta Ads mockado: parse de actions/action_values e persistência corretos")

        li_settings = SimpleNamespace(linkedin_ads_access_token="smoke-token", linkedin_ads_api_version="202504")
        li_client = httpx.Client(transport=httpx.MockTransport(linkedin_transport))
        with connect() as conn:
            records_li = linkedin_ads.sync(conn, li_client, li_settings, workspace.client_id, connection_li, DATE_FROM, DATE_TO)
        assert records_li == 1, records_li

        with connect() as conn:
            rows_li = perf_social_repo.list_linkedin_ads_daily(conn, workspace.workspace_id)
        assert len(rows_li) == 1
        assert rows_li[0]["campaign_name"] == "Campanha LinkedIn Smoke", "resolução de nome via adCampaigns falhou"
        assert rows_li[0]["spend_cents"] == 8000
        assert rows_li[0]["leads"] == 3
        print("[OK] LinkedIn Ads mockado: resolução de nome de campanha e persistência corretos")

        with connect() as conn:
            totals = perf_social_repo.get_multichannel_totals(conn, workspace.workspace_id)
        assert totals["meta"]["spend_cents"] == 12345
        assert totals["linkedin"]["spend_cents"] == 8000
        print("[OK] Totais multicanal agregados corretamente")

        print("\nPERFORMANCE SOCIAL (META/LINKEDIN ADS) SMOKE TEST OK!")
    finally:
        with connect() as conn:
            conn.execute("delete from workspace_meta_ads_daily_metrics where workspace_id = %s", (workspace.workspace_id,))
            conn.execute("delete from workspace_linkedin_ads_daily_metrics where workspace_id = %s", (workspace.workspace_id,))
        cleanup_smoke_data([workspace.organization_id], [])


if __name__ == "__main__":
    main()
