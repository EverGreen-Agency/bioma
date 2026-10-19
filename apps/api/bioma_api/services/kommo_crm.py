"""Dados reais do Kommo: painel analítico e varredura de duplicatas.

Tudo aqui apenas LÊ o Kommo. A varredura de duplicatas é sempre simulação: calcula
os pares e guarda o relatório, sem alterar contato ou lead no CRM do cliente.

Acesso:
- painel: quem enxerga a organização e tem o módulo comercial (mesma regra do
  restante da ponte Kommo);
- sincronizar e deduplicação: só EG admin. O relatório de duplicatas contém nome
  de contato e a sincronização consome a cota de API do cliente.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections import Counter
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from bioma_api import kommo_insights
from bioma_api.access import require_platform_admin
from bioma_api.crypto import decrypt_secret
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import kommo as kommo_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services.kommo import _require_access_and_module
from bioma_api.worker_bridge import _ensure_worker_in_path

_PAGE_SIZE = 250
_MAX_PAGES = 200  # 50 mil leads: teto de segurança contra paginação sem fim
ALLOWED_PERIODS = {0, 30, 90, 180}


def _credentials(conn, organization_id: UUID) -> tuple[str, str]:
    integration = kommo_repo.get_integration(conn, organization_id)
    token = decrypt_secret(integration["access_token"]) if integration else None
    if not integration or not token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kommo não conectado para esta organização. Salve as credenciais na aba Integrações.",
        )
    return integration["subdomain"], token


def _kommo_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (401, 403):
        detail = "O Kommo recusou o token salvo. Gere um novo token de longa duração e salve na aba Integrações."
    else:
        detail = "Não foi possível ler o Kommo agora. Tente novamente em instantes."
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


def _fetch_crm(subdomain: str, token: str) -> tuple[list[dict], list[dict]]:
    base_url = f"https://{subdomain}.kommo.com"
    with httpx.Client(timeout=40, headers={"Authorization": f"Bearer {token}"}) as client:
        response = client.get(f"{base_url}/api/v4/leads/pipelines")
        response.raise_for_status()
        pipelines = (response.json().get("_embedded") or {}).get("pipelines") or []

        leads: list[dict] = []
        for page in range(1, _MAX_PAGES + 1):
            response = client.get(
                f"{base_url}/api/v4/leads",
                params={"limit": _PAGE_SIZE, "page": page, "with": "loss_reason"},
            )
            if response.status_code == 204:
                break
            response.raise_for_status()
            data = response.json()
            batch = (data.get("_embedded") or {}).get("leads") or []
            if not batch:
                break
            leads.extend(batch)
            has_next = bool((data.get("_links") or {}).get("next"))
            if not has_next:
                break

        # Unsorted leads (solicitações pendentes na etapa de entrada)
        try:
            for u_page in range(1, 20):
                u_res = client.get(f"{base_url}/api/v4/leads/unsorted", params={"limit": 50, "page": u_page})
                if u_res.status_code in (204, 404):
                    break
                u_res.raise_for_status()
                u_data = u_res.json()
                u_batch = (u_data.get("_embedded") or {}).get("unsorted") or []
                if not u_batch:
                    break
                for item in u_batch:
                    pid = item.get("pipeline_id")
                    target_pipe = next((p for p in pipelines if p.get("id") == pid), pipelines[0] if pipelines else None)
                    entry_status_id = None
                    if target_pipe:
                        p_statuses = (target_pipe.get("_embedded") or {}).get("statuses") or []
                        if p_statuses:
                            sorted_statuses = sorted(p_statuses, key=lambda s: s.get("sort") or 0)
                            entry_status_id = sorted_statuses[0].get("id")
                    emb_leads = (item.get("_embedded") or {}).get("leads") or []
                    for emb_lead in emb_leads:
                        ul = dict(emb_lead)
                        ul.setdefault("pipeline_id", pid)
                        if entry_status_id and not ul.get("status_id"):
                            ul["status_id"] = entry_status_id
                        ul.setdefault("created_at", item.get("created_at") or int(time.time()))
                        ul.setdefault("updated_at", item.get("updated_at") or int(time.time()))
                        leads.append(ul)
                if not (u_data.get("_links") or {}).get("next"):
                    break
        except Exception:
            pass
    return pipelines, leads


def _dashboard_response(snapshot, configured: bool, subdomain: str | None, days: int) -> dict:
    if not snapshot:
        return {"configured": configured, "subdomain": subdomain, "fetched_at": None, "dashboard": None}
    dashboard = kommo_insights.build_dashboard(snapshot["leads"], snapshot["pipelines"], days, time.time())
    return {
        "configured": configured,
        "subdomain": snapshot["subdomain"],
        "fetched_at": snapshot["fetched_at"],
        "dashboard": dashboard,
    }


def _validate_days(days: int) -> int:
    if days not in ALLOWED_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Período inválido. Use 30, 90, 180 ou 0 (todo o histórico).",
        )
    return days


def get_dashboard(user: CurrentUserResponse, organization_id: UUID, days: int) -> dict:
    days = _validate_days(days)
    with connect() as conn:
        _require_access_and_module(conn, user, organization_id)
        config = kommo_repo.get_config_public(conn, organization_id)
        snapshot = kommo_repo.get_crm_snapshot(conn, organization_id)
    return _dashboard_response(snapshot, bool(config), config["subdomain"] if config else None, days)


def sync_dashboard(user: CurrentUserResponse, organization_id: UUID, days: int) -> dict:
    """Relê o Kommo, regrava o snapshot compacto e devolve o painel atualizado."""
    days = _validate_days(days)
    require_platform_admin(user)
    with connect() as conn:
        _require_access_and_module(conn, user, organization_id)
        subdomain, token = _credentials(conn, organization_id)

    try:
        pipelines, leads = _fetch_crm(subdomain, token)
    except httpx.HTTPError as exc:
        raise _kommo_error(exc) from exc

    compact_pipelines = kommo_insights.compact_pipelines(pipelines)
    compact_leads = [kommo_insights.compact_lead(lead) for lead in leads]

    with connect() as conn:
        kommo_repo.upsert_crm_snapshot(conn, organization_id, subdomain, compact_pipelines, compact_leads, user.id)
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "kommo.crm_synced", {"subdomain": subdomain, "leads": len(compact_leads)}
        )
        snapshot = kommo_repo.get_crm_snapshot(conn, organization_id)
    return _dashboard_response(snapshot, True, subdomain, days)


# --- Deduplicação (simulação) -------------------------------------------------

_PHONE_REASON = re.compile(r"^Telefone correspondente", re.IGNORECASE)
_EMAIL_REASON = re.compile(r"^E-mail correspondente", re.IGNORECASE)


def _match_kind(reason: str) -> str:
    if _PHONE_REASON.match(reason):
        return "Mesmo telefone"
    if _EMAIL_REASON.match(reason):
        return "Mesmo e-mail"
    return "Telefone e e-mail cruzados"


def _mask_reason(reason: str) -> str:
    """Tira o telefone/e-mail do texto do motivo: a tela mostra o tipo, não o dado."""
    return reason.split(" (")[0]


def _run_summary(row) -> dict:
    return {
        "id": row["id"],
        "subdomain": row["subdomain"],
        "contacts_scanned": row["contacts_scanned"],
        "clusters_count": row["clusters_count"],
        "duplicates_count": row["duplicates_count"],
        "leads_to_reassign": row["leads_to_reassign"],
        "created_at": row["created_at"],
        "requested_by_name": row.get("requested_by_name"),
    }


def run_dedup_simulation(user: CurrentUserResponse, organization_id: UUID) -> dict:
    require_platform_admin(user)
    with connect() as conn:
        _require_access_and_module(conn, user, organization_id)
        subdomain, token = _credentials(conn, organization_id)

    if not _ensure_worker_in_path():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Motor de deduplicação indisponível neste ambiente.",
        )
    from bioma_worker.integrations.kommo_deduplication import KommoDeduplicationEngine

    engine = KommoDeduplicationEngine(subdomain=subdomain, access_token=token)
    try:
        report = asyncio.run(engine.run_simulation()).to_dict()
    except httpx.HTTPError as exc:
        raise _kommo_error(exc) from exc

    with connect() as conn:
        inserted = kommo_repo.insert_dedup_run(conn, organization_id, user.id, subdomain, report)
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "kommo.dedup_simulated",
            {
                "subdomain": subdomain,
                "contacts_scanned": report.get("total_contacts_scanned", 0),
                "clusters": report.get("duplicate_clusters_count", 0),
            },
        )
    return {
        "id": inserted["id"],
        "subdomain": subdomain,
        "contacts_scanned": report.get("total_contacts_scanned", 0),
        "clusters_count": report.get("duplicate_clusters_count", 0),
        "duplicates_count": report.get("total_duplicates_detected", 0),
        "leads_to_reassign": report.get("total_leads_to_reassign", 0),
        "created_at": inserted["created_at"],
        "requested_by_name": user.display_name,
    }


def list_dedup_runs(user: CurrentUserResponse, organization_id: UUID) -> list[dict]:
    require_platform_admin(user)
    with connect() as conn:
        _require_access_and_module(conn, user, organization_id)
        rows = kommo_repo.list_dedup_runs(conn, organization_id)
    return [_run_summary(dict(row)) for row in rows]


def get_dedup_run(
    user: CurrentUserResponse,
    organization_id: UUID,
    run_id: UUID,
    page: int,
    page_size: int,
    only_with_leads: bool,
) -> dict:
    require_platform_admin(user)
    with connect() as conn:
        _require_access_and_module(conn, user, organization_id)
        row = kommo_repo.get_dedup_run(conn, organization_id, run_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Varredura não encontrada.")

    all_clusters = (row["report"] or {}).get("clusters") or []
    breakdown = Counter(_match_kind(cluster.get("match_reason") or "") for cluster in all_clusters)
    filtered = [c for c in all_clusters if c.get("leads_to_reassign")] if only_with_leads else all_clusters
    # Pares que exigem mover lead primeiro: são os que mudam o funil de verdade.
    filtered = sorted(filtered, key=lambda c: -len(c.get("leads_to_reassign") or []))
    start = (page - 1) * page_size
    return {
        "run": _run_summary(dict(row)),
        "match_breakdown": [
            {"label": label, "count": count, "share": count / len(all_clusters) if all_clusters else 0.0}
            for label, count in breakdown.most_common()
        ],
        "total_clusters": len(filtered),
        "page": page,
        "page_size": page_size,
        "clusters": [
            {
                "cluster_id": cluster.get("cluster_id"),
                "match_kind": _match_kind(cluster.get("match_reason") or ""),
                "match_reason": _mask_reason(cluster.get("match_reason") or ""),
                "master_contact_id": cluster.get("master_contact_id"),
                "master_name": cluster.get("master_name") or "Sem nome",
                "duplicate_contacts": [
                    {
                        "id": dup.get("id"),
                        "name": dup.get("name"),
                        "created_at": dup.get("created_at"),
                        "leads_count": dup.get("leads_count") or 0,
                    }
                    for dup in cluster.get("duplicate_contacts") or []
                ],
                "leads_to_reassign": len(cluster.get("leads_to_reassign") or []),
            }
            for cluster in filtered[start : start + page_size]
        ],
    }
