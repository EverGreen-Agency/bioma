"""Sincroniza métricas do Kommo por organização (snapshots diários por pipeline).

Segurança/robustez:
- Tokens são lidos cifrados (bioma_api.crypto) e nunca logados.
- Em 401, tenta refresh do token (exige refresh_token salvo e
  KOMMO_REDIRECT_URI no ambiente) e persiste os novos tokens cifrados.

Execução: python scripts/sync_kommo_metrics.py (manual ou job agendada).
"""

import asyncio
import datetime
import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.crypto import decrypt_secret, encrypt_secret  # noqa: E402
from bioma_api.db import connect  # noqa: E402
from bioma_api.integrations.kommo import KommoClient, KommoError  # noqa: E402
from bioma_api.repositories import kommo as kommo_repo  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sync_kommo_metrics")

# Status padrão do Kommo: 142 = ganho, 143 = perdido (demais = ativos).
KOMMO_WON_STATUS = 142
KOMMO_LOST_STATUS = 143


async def _refresh_tokens(conn, integration: dict) -> str | None:
    """Tenta renovar o access token; retorna o novo token (plaintext) ou None."""
    refresh_token = decrypt_secret(integration["refresh_token"])
    redirect_uri = os.getenv("KOMMO_REDIRECT_URI", "")
    if not refresh_token or not redirect_uri:
        logger.error(
            "Token Kommo expirado para %s e refresh indisponível "
            "(refresh_token salvo? KOMMO_REDIRECT_URI no ambiente?). "
            "Re-salve as credenciais na aba Integrações.",
            integration["subdomain"],
        )
        return None
    try:
        tokens = await KommoClient.refresh_token(
            client_id=integration["client_id"],
            client_secret=decrypt_secret(integration["client_secret"]),
            refresh_token=refresh_token,
            redirect_uri=redirect_uri,
            subdomain=integration["subdomain"],
        )
    except Exception as error:  # noqa: BLE001
        logger.error("Refresh de token Kommo falhou para %s: %s", integration["subdomain"], error)
        return None

    new_access = tokens.get("access_token")
    new_refresh = tokens.get("refresh_token")
    if not new_access:
        return None
    kommo_repo.update_tokens(
        conn,
        integration["organization_id"],
        encrypt_secret(new_access),
        encrypt_secret(new_refresh) if new_refresh else None,
    )
    logger.info("Token Kommo renovado para %s", integration["subdomain"])
    return new_access


async def _fetch_data(access_token: str, subdomain: str):
    client = KommoClient(subdomain=subdomain, access_token=access_token)
    pipelines = await client.get_pipelines()
    leads = await client.get_all_leads()
    return pipelines, leads


async def sync_organization(conn, integration: dict) -> None:
    org_id = integration["organization_id"]
    subdomain = integration["subdomain"]
    logger.info("Sincronizando Kommo da organização %s (%s)", org_id, subdomain)

    access_token = decrypt_secret(integration["access_token"])
    if not access_token:
        logger.error("Organização %s sem access_token Kommo; pulando.", org_id)
        return

    try:
        try:
            pipelines, leads = await _fetch_data(access_token, subdomain)
        except KommoError as error:
            if error.status_code != 401:
                raise
            refreshed = await _refresh_tokens(conn, integration)
            if not refreshed:
                return
            pipelines, leads = await _fetch_data(refreshed, subdomain)

        pipeline_map = {str(p["id"]): p["name"] for p in pipelines}

        metrics: dict[str, dict] = {}
        for lead in leads:
            pid = str(lead.get("pipeline_id"))
            status_id = lead.get("status_id")
            price = float(lead.get("price") or 0)

            m = metrics.setdefault(pid, {
                "total_leads": 0,
                "won_leads": 0,
                "lost_leads": 0,
                "active_leads": 0,
                "total_value": 0.0,
                "won_value": 0.0,
            })
            m["total_leads"] += 1
            m["total_value"] += price
            if status_id == KOMMO_WON_STATUS:
                m["won_leads"] += 1
                m["won_value"] += price
            elif status_id == KOMMO_LOST_STATUS:
                m["lost_leads"] += 1
            else:
                m["active_leads"] += 1

        today = datetime.date.today()
        for pid, m in metrics.items():
            conn.execute(
                """
                insert into kommo_metrics_snapshots
                  (organization_id, pipeline_id, pipeline_name, snapshot_date, total_leads,
                   won_leads, lost_leads, active_leads, total_value, won_value)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (organization_id, pipeline_id, snapshot_date)
                do update set
                    pipeline_name = excluded.pipeline_name,
                    total_leads = excluded.total_leads,
                    won_leads = excluded.won_leads,
                    lost_leads = excluded.lost_leads,
                    active_leads = excluded.active_leads,
                    total_value = excluded.total_value,
                    won_value = excluded.won_value,
                    created_at = now()
                """,
                (
                    org_id, pid, pipeline_map.get(pid, f"Pipeline {pid}"), today,
                    m["total_leads"], m["won_leads"], m["lost_leads"], m["active_leads"],
                    m["total_value"], m["won_value"],
                ),
            )
        logger.info("Organização %s sincronizada: %s pipelines, %s leads", org_id, len(metrics), len(leads))

    except KommoError as error:
        logger.error("Falha de API Kommo para %s: %s", org_id, error)
    except Exception as error:  # noqa: BLE001
        logger.error("Erro inesperado para %s: %s", org_id, error)


async def main() -> None:
    logger.info("Iniciando sync de métricas Kommo...")
    with connect() as conn:
        integrations = kommo_repo.list_integrations(conn)
        if not integrations:
            logger.info("Nenhuma integração Kommo cadastrada.")
            return
        for integration in integrations:
            await sync_organization(conn, dict(integration))

    logger.info("Sync de métricas Kommo concluído.")


if __name__ == "__main__":
    asyncio.run(main())
