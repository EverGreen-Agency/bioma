"""Radar Local — prospecção de negócios locais com aprovação humana obrigatória.

Fluxo: scan (Places API) → auditoria (IA ou prévia determinística) → revisão
humana (aprovar/rejeitar, editar mensagem) → converter em lead no CRM da EG →
envio WhatsApp. Nenhum outbound acontece sem review_status = 'approved'.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.crypto import decrypt_secret
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import local_radar as repo
from bioma_api.repositories import whatsapp as wa_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.local_radar import (
    LocalRadarImportRequest,
    LocalRadarProspect,
    LocalRadarScanCreate,
    LocalRadarScanDetail,
    LocalRadarScanSummary,
    ProspectDecisionPayload,
    ProspectMessagePayload,
    ProspectSendPayload,
    ProspectSendResult,
)
from bioma_api.worker_bridge import (
    audit_local_prospect_safe,
    get_whatsapp_provider_safe,
    normalize_imported_prospects_safe,
    search_local_businesses_safe,
)


def create_scan(payload: LocalRadarScanCreate, user: CurrentUserResponse) -> LocalRadarScanDetail:
    require_platform_admin(user)
    try:
        result = search_local_businesses_safe(
            {"niche": payload.niche, "city": payload.city, "limit": payload.limit}
        )
    except RuntimeError as exc:
        # Chave ausente ou worker fora do path: mensagem real, sem prévia inventada.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A busca no Google Places falhou. Verifique a chave e a cota da API.",
        ) from exc

    return _store_scan(user, payload.niche, payload.city, result["query_text"], "places", result["prospects"])


def import_scan(payload: LocalRadarImportRequest, user: CurrentUserResponse) -> LocalRadarScanDetail:
    """Entrada alternativa sem custo de API: planilha exportada por extensão de
    scrape (ex.: Instant Data Scraper) parseada no navegador. Mesmo pipeline de
    score, auditoria e aprovação da busca via Places."""
    require_platform_admin(user)
    prospects = normalize_imported_prospects_safe([row.model_dump() for row in payload.rows])
    if not prospects:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhuma linha com nome de negócio reconhecível na planilha.",
        )
    query_text = f"{payload.niche} em {payload.city} (importado)"
    return _store_scan(user, payload.niche, payload.city, query_text, "import", prospects)


def _store_scan(
    user: CurrentUserResponse,
    niche: str,
    city: str,
    query_text: str,
    source: str,
    prospects: list[dict],
) -> LocalRadarScanDetail:
    with connect() as conn:
        # Diff contra o snapshot anterior de cada place_id: é o sinal de rescan
        # ("criou site", "nota caiu") e a deduplicação de quem já virou lead.
        previous = repo.previous_prospects_by_place(conn, [p["place_id"] for p in prospects])
        for prospect in prospects:
            prospect["changes"] = _diff_changes(previous.get(prospect["place_id"]), prospect)

        scan = repo.create_scan(
            conn,
            user.id,
            {"niche": niche, "city": city, "query_text": query_text, "status": "completed", "source": source},
        )
        repo.insert_prospects(conn, scan["id"], prospects)
        scan = repo.get_scan(conn, scan["id"])
        rows = repo.list_prospects(conn, scan["id"])
        client_hub_repo.write_audit(
            conn,
            user.id,
            None,
            "local_radar.scan_created",
            {"scan_id": str(scan["id"]), "niche": niche, "city": city, "source": source, "count": scan["prospect_count"]},
        )
    return _detail(scan, rows)


def _diff_changes(previous: dict | None, current: dict) -> list[str]:
    if not previous:
        return []
    changes: list[str] = []
    if not previous["website"] and current.get("website"):
        changes.append("Criou site desde o último scan")
    if previous["website"] and not current.get("website"):
        changes.append("Site sumiu do Google desde o último scan")
    if not previous["phone"] and current.get("phone"):
        changes.append("Cadastrou telefone desde o último scan")
    old_rating = float(previous["rating"]) if previous["rating"] is not None else None
    new_rating = current.get("rating")
    if old_rating is not None and new_rating is not None and abs(new_rating - old_rating) >= 0.2:
        changes.append(f"Nota mudou de {old_rating} para {new_rating}")
    old_count = previous["rating_count"] or 0
    new_count = current.get("rating_count") or 0
    if new_count - old_count >= 10:
        changes.append(f"+{new_count - old_count} avaliações desde o último scan")
    if previous["lead_id"]:
        changes.append("Já é lead no CRM da EG (scan anterior)")
    return changes


def list_scans(user: CurrentUserResponse) -> list[LocalRadarScanSummary]:
    require_platform_admin(user)
    with connect() as conn:
        rows = repo.list_scans(conn)
    return [LocalRadarScanSummary(**row) for row in rows]


def get_scan(scan_id: UUID, user: CurrentUserResponse) -> LocalRadarScanDetail:
    require_platform_admin(user)
    with connect() as conn:
        scan = repo.get_scan(conn, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan não encontrado.")
        prospects = repo.list_prospects(conn, scan_id)
    return _detail(scan, prospects)


def run_audit(prospect_id: UUID, user: CurrentUserResponse) -> LocalRadarProspect:
    require_platform_admin(user)
    with connect() as conn:
        prospect = _require_prospect(conn, prospect_id)
        if prospect["review_status"] in ("approved", "sent"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prospect já aprovado — reauditar sobrescreveria a mensagem revisada.",
            )

    prospect_input = {
        **prospect,
        "rating": float(prospect["rating"]) if prospect["rating"] is not None else None,
    }
    # Se existe pesquisa de mercado concluída para o nicho do scan, o playbook
    # de prospecção dela alimenta a mensagem — abordagem consultiva por setor.
    playbook = None
    with connect() as conn:
        scan = repo.get_scan(conn, prospect["scan_id"])
        if scan:
            playbook = repo.latest_research_playbook(conn, scan["niche"])
    try:
        result = audit_local_prospect_safe(prospect_input, playbook=(playbook or {}).get("playbook"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A auditoria de IA falhou. Tente novamente.",
        ) from exc

    audit_payload = dict(result["audit"])
    if playbook:
        # Rastreabilidade: qual pesquisa alimentou esta mensagem.
        audit_payload["research_used"] = {"id": playbook["research_id"], "sector": playbook["sector"]}

    with connect() as conn:
        updated = repo.update_prospect(
            conn,
            prospect_id,
            {
                "audit": audit_payload,
                "audit_mode": result["audit_mode"],
                "outreach_message": result["suggested_message"],
                "review_status": "audited",
            },
        )
    return _prospect(updated)


def update_message(prospect_id: UUID, payload: ProspectMessagePayload, user: CurrentUserResponse) -> LocalRadarProspect:
    require_platform_admin(user)
    with connect() as conn:
        prospect = _require_prospect(conn, prospect_id)
        if prospect["review_status"] == "sent":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mensagem já enviada.")
        updated = repo.update_prospect(conn, prospect_id, {"outreach_message": payload.message})
    return _prospect(updated)


def decide(prospect_id: UUID, payload: ProspectDecisionPayload, user: CurrentUserResponse) -> LocalRadarProspect:
    require_platform_admin(user)
    now = datetime.now(timezone.utc)
    with connect() as conn:
        prospect = _require_prospect(conn, prospect_id)
        if prospect["review_status"] == "sent":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mensagem já enviada.")

        updates: dict = {"review_status": payload.decision, "reviewed_by": user.id, "reviewed_at": now}

        if payload.decision == "approved":
            if not prospect["audit"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Rode a auditoria antes de aprovar: a aprovação exige diagnóstico revisável.",
                )
            if not prospect["lead_id"]:
                context = repo.eg_context(conn)
                if not context:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Organização EG não encontrada para receber o lead.",
                    )
                diagnosis = (prospect["audit"] or {}).get("diagnosis", "")
                notes_parts = [part for part in (diagnosis, prospect.get("google_maps_url")) if part]
                lead_id = client_hub_repo.create_lead(
                    conn,
                    context["organization_id"],
                    {
                        "name": prospect["name"],
                        "company": prospect["name"],
                        "phone": prospect.get("phone"),
                        "source": "radar_local",
                        "stage": "new",
                        "notes": "\n\n".join(notes_parts) or None,
                    },
                )
                updates["lead_id"] = lead_id

        updated = repo.update_prospect(conn, prospect_id, updates)
        client_hub_repo.write_audit(
            conn,
            user.id,
            None,
            f"local_radar.prospect_{payload.decision}",
            {"prospect_id": str(prospect_id), "name": prospect["name"]},
        )
    return _prospect(updated)


def send_whatsapp(prospect_id: UUID, payload: ProspectSendPayload, user: CurrentUserResponse) -> ProspectSendResult:
    require_platform_admin(user)
    with connect() as conn:
        prospect = _require_prospect(conn, prospect_id)
        if prospect["review_status"] != "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Só prospects aprovados por um humano podem receber mensagem.",
            )
        if not prospect.get("phone"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prospect sem telefone.")
        if not prospect.get("outreach_message"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prospect sem mensagem de abordagem.")

        context = repo.eg_context(conn)
        if not context:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace interno da EG não encontrado.")

        config_row = wa_repo.get_provider_config(conn, context["workspace_id"], payload.provider_type)
        config_dict = dict(config_row) if config_row else {"provider_type": payload.provider_type}
        if config_dict.get("api_token"):
            config_dict["api_token"] = decrypt_secret(config_dict["api_token"])
        provider = get_whatsapp_provider_safe(payload.provider_type, config_dict)

        to_number = "".join(ch for ch in prospect["phone"] if ch.isdigit())
        result = provider.send_text_message(to_number, prospect["outreach_message"])
        send_status = result.get("status", "failed")

        wa_repo.log_message(
            conn,
            context["workspace_id"],
            {
                "provider_type": payload.provider_type,
                "to_number": to_number,
                "message_type": "text",
                "payload": result,
                "status": "sent" if send_status in ("sent", "simulated") else "failed",
                "error_message": result.get("error"),
            },
        )

        # "simulated" (provider sem credencial) NÃO marca como enviado: a mensagem
        # não chegou a ninguém e o prospect continua elegível para envio real.
        if send_status == "sent":
            updated = repo.update_prospect(
                conn, prospect_id, {"review_status": "sent", "sent_at": datetime.now(timezone.utc)}
            )
        else:
            updated = prospect

        detail = None
        if send_status == "simulated":
            detail = "Provider em modo simulação (sem credencial configurada) — nada foi enviado."
        elif send_status == "failed":
            detail = result.get("error") or "Falha no envio."

    return ProspectSendResult(prospect=_prospect(updated), send_status=send_status, detail=detail)


def _require_prospect(conn, prospect_id: UUID) -> dict:
    prospect = repo.get_prospect(conn, prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect não encontrado.")
    return prospect


def _prospect(row: dict) -> LocalRadarProspect:
    data = dict(row)
    if data.get("rating") is not None:
        data["rating"] = float(data["rating"])
    return LocalRadarProspect(**data)


def _detail(scan: dict, prospects: list[dict]) -> LocalRadarScanDetail:
    return LocalRadarScanDetail(**scan, prospects=[_prospect(row) for row in prospects])
