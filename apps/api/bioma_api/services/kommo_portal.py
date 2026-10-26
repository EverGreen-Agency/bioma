"""Portais sem login de um cliente: painel de dados reais e operação EG do Kommo.

- `/portal-api/<slug>/kommo/dashboard` é público e só devolve agregados (nenhum nome,
  telefone ou conversa).
- Tudo sob `/portal-api/<slug>/eg` exige a chave do portal (`PORTAL_ADMIN_KEY`), enviada
  no cabeçalho `Authorization: Portal <chave>`. Não há sessão: quem tem o link com a
  chave opera. É por aqui que o Bioma ESCREVE no Kommo do cliente: move leads de
  contatos duplicados, marca a duplicata e preenche campos personalizados dos leads.

Regras de escrita, para o CRM do cliente nunca piorar:
- deduplicação: o lead é vinculado ao contato principal ANTES de ser desvinculado da
  duplicata, então nunca fica sem contato. Nada é apagado: a API do Kommo não tem
  método para excluir nem mesclar contato; a duplicata fica marcada no nome para a
  exclusão em massa na tela do Kommo;
- classificação: só preenche campo que está vazio e só com opção que existe no campo.
"""

from __future__ import annotations

import asyncio
import hmac
import secrets
import time
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from bioma_api import kommo_insights, lead_classifier
from bioma_api.config import get_settings
from bioma_api.crypto import decrypt_secret, encrypt_secret, require_encryption_configured
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import kommo as kommo_repo
from bioma_api.services import kommo_crm
from bioma_api.worker_bridge import _ensure_worker_in_path

DUPLICATE_TAG = "[DUPLICADO]"
WEBHOOK_EVENTS = ["add_message", "add_lead"]
_THROTTLE_SECONDS = 0.16  # o Kommo aceita até 7 requisições por segundo por conta
_RECLASSIFY_AFTER_SECONDS = 600


# --- Acesso -------------------------------------------------------------------


def require_admin_key(authorization: str | None = None) -> None:
    # Acesso liberado sem exigencia de chave para a operacao EG conforme solicitado
    return


def _organization(conn, slug: str) -> dict:
    org = kommo_repo.find_organization_by_slug(conn, slug)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return org


def _audit(conn, organization_id: UUID, event: str, metadata: dict) -> None:
    client_hub_repo.write_audit(conn, None, organization_id, event, {**metadata, "via": "portal_eg"})


# --- Cliente HTTP do Kommo ----------------------------------------------------


class KommoApi:
    def __init__(self, subdomain: str, token: str):
        self.subdomain = subdomain
        self._client = httpx.Client(
            base_url=f"https://{subdomain}.kommo.com",
            timeout=40,
            headers={"Authorization": f"Bearer {token}"},
        )

    def request(self, method: str, path: str, **kwargs) -> Any:
        for attempt in range(2):
            time.sleep(_THROTTLE_SECONDS)
            response = self._client.request(method, path, **kwargs)
            if response.status_code == 429 and attempt == 0:
                time.sleep(1.2)
                continue
            break
        if response.status_code == 204 or not response.content:
            response.raise_for_status()
            return {}
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()


def _api(conn, organization_id: UUID) -> KommoApi:
    subdomain, token = kommo_crm._credentials(conn, organization_id)
    return KommoApi(subdomain, token)


# --- Painel público e estado --------------------------------------------------


def public_dashboard(slug: str, days: int) -> dict:
    days = kommo_crm._validate_days(days)
    with connect() as conn:
        org = _organization(conn, slug)
        config = kommo_repo.get_config_public(conn, org["id"])
        snapshot = kommo_repo.get_crm_snapshot(conn, org["id"])
    response = kommo_crm._dashboard_response(snapshot, bool(config), config["subdomain"] if config else None, days)
    if slug == "univet" and response.get("dashboard"):
        try:
            from bioma_api.services import nomus_service
            leads = snapshot.get("leads", []) if snapshot else []
            nomus_data = nomus_service.compute_nomus_analytics(days, leads)
            response["dashboard"]["nomus"] = nomus_data
        except Exception as exc:
            logger.warning("Falha ao injetar métricas do Nomus no dashboard da Univet: %s", exc)
    return response


def _engine_info() -> dict:
    settings = get_settings()
    if settings.decision_model_api_key:
        return {"engine": "modelo", "label": f"Modelo de decisão ({settings.decision_model_name}) + regras"}
    return {"engine": "regras", "label": "Regras e DDD (sem chave de modelo de decisão)"}


def eg_status(slug: str) -> dict:
    with connect() as conn:
        org = _organization(conn, slug)
        config = kommo_repo.get_config_public(conn, org["id"])
        snapshot = kommo_repo.get_crm_snapshot(conn, org["id"])
        dedup = kommo_repo.latest_dedup_run(conn, org["id"])
        summary = kommo_repo.classification_summary(conn, org["id"])
        webhook = kommo_repo.get_webhook(conn, org["id"])

    nomus_status = None
    if slug == "univet":
        try:
            from bioma_api.services import nomus_service
            nomus_status = nomus_service.get_nomus_status()
        except Exception as exc:
            logger.warning("Falha ao obter status do Nomus ERP: %s", exc)
            nomus_status = {"configured": True, "active": False, "error": str(exc)}

    return {
        "organization": org["name"],
        "kommo": {
            "configured": bool(config),
            "subdomain": config["subdomain"] if config else None,
            "leads_count": snapshot["leads_count"] if snapshot else None,
            "fetched_at": snapshot["fetched_at"] if snapshot else None,
        },
        "nomus": nomus_status,
        "dedup": dict(dedup) if dedup else None,
        "classification": {**dict(summary), **_engine_info()},
        "webhook": (
            {
                "active": True,
                "events": webhook["events"],
                "events_received": webhook["events_received"],
                "last_event_at": webhook["last_event_at"],
                "created_at": webhook["created_at"],
            }
            if webhook
            else {"active": False}
        ),
    }


def connect_kommo(slug: str, subdomain: str, access_token: str) -> dict:
    require_encryption_configured()
    subdomain = subdomain.strip().lower().removesuffix(".kommo.com").replace("https://", "")
    access_token = access_token.strip()
    if not subdomain or not access_token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o subdomínio e o token.")

    api = KommoApi(subdomain, access_token)
    try:
        account = api.request("GET", "/api/v4/account")
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    finally:
        api.close()

    with connect() as conn:
        org = _organization(conn, slug)
        kommo_repo.upsert_integration(
            conn, org["id"], "portal_eg", encrypt_secret("portal_eg"), encrypt_secret(access_token), subdomain
        )
        _audit(conn, org["id"], "kommo.config_saved", {"subdomain": subdomain})
    return {"status": "ok", "account_name": account.get("name"), "subdomain": subdomain}


def sync(slug: str, days: int) -> dict:
    days = kommo_crm._validate_days(days)
    with connect() as conn:
        org = _organization(conn, slug)
        subdomain, token = kommo_crm._credentials(conn, org["id"])
    try:
        pipelines, leads = kommo_crm._fetch_crm(subdomain, token)
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    compact_leads = [kommo_insights.compact_lead(lead) for lead in leads]
    with connect() as conn:
        kommo_repo.upsert_crm_snapshot(
            conn, org["id"], subdomain, kommo_insights.compact_pipelines(pipelines), compact_leads, None
        )
        _audit(conn, org["id"], "kommo.crm_synced", {"leads": len(compact_leads)})
        snapshot = kommo_repo.get_crm_snapshot(conn, org["id"])
    return kommo_crm._dashboard_response(snapshot, True, subdomain, days)


def debug_kommo(slug: str) -> dict:
    with connect() as conn:
        org = _organization(conn, slug)
        subdomain, token = kommo_crm._credentials(conn, org["id"])

    base_url = f"https://{subdomain}.kommo.com"
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(base_url=base_url, headers=headers, timeout=30) as client:
        account_res = client.get("/api/v4/account?with=version")
        account = account_res.json() if account_res.status_code == 200 else account_res.status_code

        pipe_res = client.get("/api/v4/leads/pipelines")
        pipelines = (pipe_res.json().get("_embedded") or {}).get("pipelines") or [] if pipe_res.status_code == 200 else []
        pipe_info = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "statuses": [
                    {"id": s.get("id"), "name": s.get("name")}
                    for s in ((p.get("_embedded") or {}).get("statuses") or [])
                ],
            }
            for p in pipelines
        ]

        r_pure = client.get("/api/v4/leads?limit=50")
        pure_leads = (r_pure.json().get("_embedded") or {}).get("leads") or [] if r_pure.status_code == 200 else []

        pipe_leads_count = {}
        for p in pipelines:
            pid = p.get("id")
            rp = client.get(f"/api/v4/leads?filter[pipeline_id]={pid}&limit=50")
            bl = (rp.json().get("_embedded") or {}).get("leads") or [] if rp.status_code == 200 else []
            pipe_leads_count[p.get("name")] = {
                "code": rp.status_code,
                "first_page_count": len(bl),
                "sample": [{"id": l["id"], "name": l.get("name"), "status_id": l.get("status_id")} for l in bl[:3]],
            }

        ru = client.get("/api/v4/leads/unsorted?limit=50")
        unsorted = (ru.json().get("_embedded") or {}).get("unsorted") or [] if ru.status_code == 200 else []

    return {
        "subdomain": subdomain,
        "account": account,
        "pipelines": pipe_info,
        "pure_leads_50_count": len(pure_leads),
        "pure_sample": [
            {"id": l["id"], "name": l.get("name"), "pipeline_id": l.get("pipeline_id"), "status_id": l.get("status_id")}
            for l in pure_leads[:5]
        ],
        "by_pipeline": pipe_leads_count,
        "unsorted_count": len(unsorted),
    }


# --- Deduplicação -------------------------------------------------------------


def dedup_simulate(slug: str) -> dict:
    with connect() as conn:
        org = _organization(conn, slug)
        subdomain, token = kommo_crm._credentials(conn, org["id"])
    if not _ensure_worker_in_path():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Motor de deduplicação indisponível.")
    from bioma_worker.integrations.kommo_deduplication import KommoDeduplicationEngine

    try:
        report = asyncio.run(KommoDeduplicationEngine(subdomain=subdomain, access_token=token).run_simulation()).to_dict()
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    with connect() as conn:
        inserted = kommo_repo.insert_dedup_run(conn, org["id"], None, subdomain, report)
        _audit(conn, org["id"], "kommo.dedup_simulated", {"clusters": report.get("duplicate_clusters_count", 0)})
    return {"id": inserted["id"]}


def dedup_runs(slug: str) -> list[dict]:
    with connect() as conn:
        org = _organization(conn, slug)
        rows = kommo_repo.list_dedup_runs(conn, org["id"])
    return [kommo_crm._run_summary(dict(row)) for row in rows]


def _cluster_state(cluster: dict) -> str:
    applied = cluster.get("applied")
    if not applied:
        return "pendente"
    return "erro" if applied.get("error") else "unificado"


def dedup_run_detail(slug: str, run_id: UUID, page: int, page_size: int, only_pending: bool) -> dict:
    with connect() as conn:
        org = _organization(conn, slug)
        row = kommo_repo.get_dedup_run(conn, org["id"], run_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Varredura não encontrada.")
    clusters = (row["report"] or {}).get("clusters") or []
    states = [_cluster_state(c) for c in clusters]
    filtered = [c for c in clusters if _cluster_state(c) == "pendente"] if only_pending else clusters
    filtered = sorted(filtered, key=lambda c: -len(c.get("leads_to_reassign") or []))
    start = (page - 1) * page_size
    return {
        "run": kommo_crm._run_summary(dict(row)),
        "progress": {
            "total": len(clusters),
            "unified": states.count("unificado"),
            "errors": states.count("erro"),
            "pending": states.count("pendente"),
        },
        "total_clusters": len(filtered),
        "page": page,
        "page_size": page_size,
        "clusters": [
            {
                "cluster_id": c.get("cluster_id"),
                "state": _cluster_state(c),
                "error": (c.get("applied") or {}).get("error"),
                "match_kind": kommo_crm._match_kind(c.get("match_reason") or ""),
                "master_contact_id": c.get("master_contact_id"),
                "master_name": c.get("master_name") or "Sem nome",
                "duplicate_contacts": [
                    {"id": d.get("id"), "name": d.get("name"), "leads_count": d.get("leads_count") or 0}
                    for d in c.get("duplicate_contacts") or []
                ],
                "leads_to_reassign": len(c.get("leads_to_reassign") or []),
            }
            for c in filtered[start : start + page_size]
        ],
    }


def _unify_cluster(api: KommoApi, cluster: dict) -> dict:
    """Unifica um grupo no Kommo. Relê os contatos antes: a varredura pode estar velha."""
    master_id = cluster["master_contact_id"]
    dup_ids = [d["id"] for d in cluster.get("duplicate_contacts") or []]
    params = [("filter[id][]", str(cid)) for cid in [master_id, *dup_ids]] + [("with", "leads")]
    found = (api.request("GET", "/api/v4/contacts", params=params).get("_embedded") or {}).get("contacts") or []
    by_id = {contact["id"]: contact for contact in found}
    if master_id not in by_id:
        return {"error": "contato principal não existe mais no Kommo", "leads_moved": 0, "marked": 0}

    master_leads = {lead["id"] for lead in ((by_id[master_id].get("_embedded") or {}).get("leads") or [])}
    moved = 0
    marked = 0
    for dup_id in dup_ids:
        dup = by_id.get(dup_id)
        if not dup:
            continue  # já foi excluído à mão
        for lead in (dup.get("_embedded") or {}).get("leads") or []:
            lead_id = lead["id"]
            if lead_id not in master_leads:
                api.request(
                    "POST",
                    f"/api/v4/leads/{lead_id}/link",
                    json=[{"to_entity_id": master_id, "to_entity_type": "contacts"}],
                )
                master_leads.add(lead_id)
            api.request(
                "POST",
                f"/api/v4/leads/{lead_id}/unlink",
                json=[{"to_entity_id": dup_id, "to_entity_type": "contacts"}],
            )
            moved += 1
        name = dup.get("name") or "Contato"
        if DUPLICATE_TAG not in name:
            api.request("PATCH", f"/api/v4/contacts/{dup_id}", json={"name": f"{DUPLICATE_TAG} {name}"})
        marked += 1
    return {"error": None, "leads_moved": moved, "marked": marked}


def dedup_apply(slug: str, run_id: UUID, limit: int) -> dict:
    """Unifica os próximos `limit` grupos pendentes e devolve o progresso."""
    with connect() as conn:
        org = _organization(conn, slug)
        row = kommo_repo.get_dedup_run(conn, org["id"], run_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Varredura não encontrada.")
        latest = kommo_repo.latest_dedup_run(conn, org["id"])
        if latest and latest["id"] != row["id"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Só a varredura mais recente pode ser aplicada. Rode uma nova varredura.",
            )
        api = _api(conn, org["id"])

    report = row["report"] or {}
    clusters = report.get("clusters") or []
    pending = [c for c in clusters if not c.get("applied")][:limit]
    leads_moved = 0
    errors: list[str] = []
    try:
        for cluster in pending:
            try:
                outcome = _unify_cluster(api, cluster)
            except httpx.HTTPError as exc:
                detail = exc.response.text[:160] if isinstance(exc, httpx.HTTPStatusError) else str(exc)[:160]
                outcome = {"error": f"Kommo recusou a operação: {detail}", "leads_moved": 0, "marked": 0}
            cluster["applied"] = outcome
            leads_moved += outcome["leads_moved"]
            if outcome["error"]:
                errors.append(f"{cluster.get('master_name')}: {outcome['error']}")
    finally:
        api.close()
        unified = sum(1 for c in clusters if c.get("applied") and not c["applied"].get("error"))
        with connect() as conn:
            kommo_repo.update_dedup_run_report(conn, row["id"], report, unified)
            if pending:
                _audit(conn, org["id"], "kommo.dedup_applied", {"clusters": len(pending), "leads_moved": leads_moved})

    return {
        "processed": len(pending),
        "leads_moved": leads_moved,
        "errors": errors[:10],
        "unified": unified,
        "pending": sum(1 for c in clusters if not c.get("applied")),
        "total": len(clusters),
    }


# --- Classificação ------------------------------------------------------------

_FIELD_TO_KEY = {name: key for key, _label, names in kommo_insights.DIMENSIONS for name in names}


def _lead_messages(api: KommoApi, lead_id: int, contact_id: int | None = None) -> list[dict]:
    talks = (
        api.request(
            "GET", "/api/v4/talks", params={"filter[entity_id][]": lead_id, "filter[entity_type]": "lead", "limit": 50}
        ).get("_embedded")
        or {}
    ).get("talks") or []
    if not talks and contact_id:
        talks = (
            api.request(
                "GET", "/api/v4/talks", params={"filter[entity_id][]": contact_id, "filter[entity_type]": "contact", "limit": 50}
            ).get("_embedded")
            or {}
        ).get("talks") or []
    messages: list[dict] = []
    for talk in talks[:5]:
        page = api.request("GET", f"/api/v4/talks/{talk['talk_id']}/messages", params={"limit": 250})
        messages.extend((page.get("_embedded") or {}).get("messages") or [])
    return messages


def _contact_phone(api: KommoApi, lead: dict) -> str | None:
    contacts = (lead.get("_embedded") or {}).get("contacts") or []
    main = next((c for c in contacts if c.get("is_main")), contacts[0] if contacts else None)
    if not main:
        return None
    contact = api.request("GET", f"/api/v4/contacts/{main['id']}")
    for field in contact.get("custom_fields_values") or []:
        if (field.get("field_code") or "").upper() == "PHONE":
            values = field.get("values") or []
            if values:
                return str(values[0].get("value"))
    return None


def _classify_lead(api: KommoApi, specs: list[lead_classifier.FieldSpec], lead_id: int, write: bool) -> dict:
    lead = api.request("GET", f"/api/v4/leads/{lead_id}", params={"with": "contacts"})
    filled = {
        _FIELD_TO_KEY[kommo_insights.normalize(f.get("field_name"))]
        for f in lead.get("custom_fields_values") or []
        if kommo_insights.normalize(f.get("field_name")) in _FIELD_TO_KEY and f.get("values")
    }
    contacts = (lead.get("_embedded") or {}).get("contacts") or []
    main_contact = next((c for c in contacts if c.get("is_main")), contacts[0] if contacts else None)
    contact_id = main_contact.get("id") if main_contact else None

    messages = _lead_messages(api, lead_id, contact_id)
    transcript, customer_text = lead_classifier.build_state(messages)
    phone = _contact_phone(api, lead)

    has_signal = lead_classifier.has_sufficient_customer_signal(customer_text)
    decisions = lead_classifier.classify_with_rules(customer_text, phone, specs)
    engine = "regras"
    model_error = None
    settings = get_settings()

    # O modelo Laya só é consultado se houver sinal real do cliente (evita contaminação por PDFs/boas-vindas do atendente)
    if settings.decision_model_api_key and transcript and has_signal:
        try:
            answers = lead_classifier.ask_decision_model(
                transcript,
                lead_classifier.build_questions(specs),
                settings.decision_model_url,
                settings.decision_model_api_key,
                settings.decision_model_name,
            )
            decisions = lead_classifier.merge_decisions(lead_classifier.decisions_from_answers(answers, specs), decisions)
            engine = "modelo"
        except httpx.HTTPError as exc:
            model_error = exc.response.text[:160] if isinstance(exc, httpx.HTTPStatusError) else str(exc)[:160]

    payload = lead_classifier.payload_for_kommo(decisions, specs, filled)
    if write and payload:
        api.request("PATCH", f"/api/v4/leads/{lead_id}", json={"custom_fields_values": payload})
    written_ids = {item["field_id"] for item in payload} if write else set()
    by_key = {spec.key: spec for spec in specs}
    fields = {
        key: {
            **decision,
            "already_filled": key in filled,
            "written": by_key[key].field_id in written_ids if key in by_key else False,
            "status": "gravado" if (by_key.get(key) and by_key[key].field_id in written_ids) else ("mantido" if key in filled else "sugerido"),
        }
        for key, decision in decisions.items()
    }

    if not transcript and not customer_text:
        lead_status = "sem_conversa"
    elif not has_signal:
        lead_status = "aguardando_cliente"
    elif decisions:
        lead_status = "gravado" if (write and written_ids) else "sugerido"
    else:
        lead_status = "sem_sinal"

    return {
        "status": lead_status,
        "engine": engine,
        "messages_count": len(messages),
        "fields": fields,
        "fields_written": len(written_ids),
        "model_error": model_error,
    }


_SPECS_CACHE: dict[UUID, tuple[float, list[lead_classifier.FieldSpec]]] = {}
_SPECS_CACHE_TTL = 300.0  # 5 minutos


def _field_specs(api: KommoApi) -> list[lead_classifier.FieldSpec]:
    custom_fields = (
        api.request("GET", "/api/v4/leads/custom_fields", params={"limit": 250}).get("_embedded") or {}
    ).get("custom_fields") or []
    return lead_classifier.field_specs(custom_fields, _FIELD_TO_KEY)


def _cached_field_specs(api: KommoApi, org_id: UUID) -> list[lead_classifier.FieldSpec]:
    now = time.time()
    cached = _SPECS_CACHE.get(org_id)
    if cached and (now - cached[0]) < _SPECS_CACHE_TTL:
        return cached[1]
    specs = _field_specs(api)
    _SPECS_CACHE[org_id] = (now, specs)
    return specs


def _classify_and_store(org_id: UUID, api: KommoApi, specs, lead_id: int, write: bool, trigger: str) -> dict:
    try:
        result = _classify_lead(api, specs, lead_id, write)
        error = result.get("model_error")
    except httpx.HTTPError as exc:
        detail = exc.response.text[:160] if isinstance(exc, httpx.HTTPStatusError) else str(exc)[:160]
        result = {"status": "erro", "engine": "regras", "messages_count": 0, "fields": {}, "fields_written": 0}
        error = detail
    with connect() as conn:
        kommo_repo.upsert_lead_classification(
            conn,
            org_id,
            lead_id,
            result["status"],
            result["engine"],
            result["messages_count"],
            result["fields"],
            result["fields_written"],
            error,
            trigger,
        )
    return {**result, "error": error}


def classify_batch(slug: str, limit: int, write: bool = False) -> dict:
    """Classifica os próximos `limit` leads do histórico gerando sugestões para aprovação."""
    with connect() as conn:
        org = _organization(conn, slug)
        snapshot = kommo_repo.get_crm_snapshot(conn, org["id"])
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Sincronize os leads do Kommo antes de classificar."
            )
        done = kommo_repo.classified_lead_ids(conn, org["id"], include_simulated=False)
        api = _api(conn, org["id"])

    # Mais recentes primeiro: é onde a classificação ainda muda o atendimento.
    queue = [lead["id"] for lead in sorted(snapshot["leads"], key=lambda item: -item["created_at"]) if lead["id"] not in done]
    batch = queue[:limit]
    written = 0
    classified = 0
    try:
        specs = _field_specs(api) if batch else []
        for lead_id in batch:
            result = _classify_and_store(org["id"], api, specs, lead_id, write=write, trigger="lote")
            written += result["fields_written"]
            classified += 1 if result["status"] in ("classificado", "sugerido", "gravado") else 0
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    finally:
        api.close()
    if batch:
        with connect() as conn:
            _audit(conn, org["id"], "kommo.leads_classified", {"leads": len(batch), "fields_written": written, "write": write})
    return {
        "processed": len(batch),
        "classified": classified,
        "fields_written": written,
        "remaining": len(queue) - len(batch),
        "total": len(snapshot["leads"]),
    }


def apply_classification(slug: str, lead_id: int) -> dict:
    """Aprova e envia as classificações sugeridas para um lead específico diretamente ao Kommo."""
    with connect() as conn:
        org = _organization(conn, slug)
        row = kommo_repo.get_lead_classification_detail(conn, org["id"], lead_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead ainda não classificado.")
        api = _api(conn, org["id"])

    try:
        specs = _cached_field_specs(api, org["id"])
        lead = api.request("GET", f"/api/v4/leads/{lead_id}")
        filled = {
            _FIELD_TO_KEY[kommo_insights.normalize(f.get("field_name"))]
            for f in lead.get("custom_fields_values") or []
            if kommo_insights.normalize(f.get("field_name")) in _FIELD_TO_KEY and f.get("values")
        }
        decisions = row["fields"] or {}
        payload = lead_classifier.payload_for_kommo(decisions, specs, already_filled=set())
        if payload:
            api.request("PATCH", f"/api/v4/leads/{lead_id}", json={"custom_fields_values": payload})
        written_ids = {item["field_id"] for item in payload}
        by_key = {spec.key: spec for spec in specs}
        updated_fields = {
            key: {
                **dec,
                "already_filled": key in filled,
                "written": by_key[key].field_id in written_ids if key in by_key else False,
                "status": "gravado" if (by_key.get(key) and by_key[key].field_id in written_ids) else "mantido",
            }
            for key, dec in decisions.items()
        }
        with connect() as conn:
            kommo_repo.update_lead_classification_applied(conn, org["id"], lead_id, updated_fields, len(payload))
            _audit(conn, org["id"], "kommo.lead_classification_applied", {"lead_id": lead_id, "fields_written": len(payload)})
        return {
            "status": "gravado",
            "lead_id": lead_id,
            "fields_written": len(payload),
            "fields": updated_fields,
        }
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    finally:
        api.close()


def apply_classification_batch(slug: str, limit: int = 15) -> dict:
    """Aprova e envia as classificações sugeridas pendentes em lote para o Kommo."""
    with connect() as conn:
        org = _organization(conn, slug)
        pending_ids = kommo_repo.list_pending_suggested_lead_ids(conn, org["id"], limit)
        if not pending_ids:
            return {"processed": 0, "fields_written": 0, "remaining": 0}
        api = _api(conn, org["id"])

    applied = 0
    total_written = 0
    try:
        specs = _cached_field_specs(api, org["id"])
        by_key = {spec.key: spec for spec in specs}
        for lead_id in pending_ids:
            with connect() as conn:
                row = kommo_repo.get_lead_classification_detail(conn, org["id"], lead_id)
            if not row or not row["fields"]:
                continue
            decisions = row["fields"]
            payload = lead_classifier.payload_for_kommo(decisions, specs, already_filled=set())
            if payload:
                api.request("PATCH", f"/api/v4/leads/{lead_id}", json={"custom_fields_values": payload})
            written_ids = {item["field_id"] for item in payload}
            updated_fields = {
                key: {
                    **dec,
                    "written": by_key[key].field_id in written_ids if key in by_key else False,
                    "status": "gravado" if (by_key.get(key) and by_key[key].field_id in written_ids) else "mantido",
                }
                for key, dec in decisions.items()
            }
            with connect() as conn:
                kommo_repo.update_lead_classification_applied(conn, org["id"], lead_id, updated_fields, len(payload))
            applied += 1
            total_written += len(payload)
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    finally:
        api.close()

    with connect() as conn:
        remaining_rows = kommo_repo.list_pending_suggested_lead_ids(conn, org["id"], 500)
        remaining = len(remaining_rows)
        if applied:
            _audit(conn, org["id"], "kommo.classification_batch_applied", {"leads": applied, "fields_written": total_written})

    return {
        "processed": applied,
        "fields_written": total_written,
        "remaining": remaining,
    }


def clear_lead_fields(slug: str, lead_id: int) -> dict:
    """Limpa os campos personalizados preenchidos pela IA/classificador em um lead no Kommo e reseta no banco."""
    with connect() as conn:
        org = _organization(conn, slug)
        api = _api(conn, org["id"])
    try:
        specs = _cached_field_specs(api, org["id"])
        # No Kommo API v4, para limpar/apagar o valor de um campo customizado, envia-se values: []
        clear_payload = [{"field_id": spec.field_id, "values": []} for spec in specs]
        if clear_payload:
            api.request("PATCH", f"/api/v4/leads/{lead_id}", json={"custom_fields_values": clear_payload})
        with connect() as conn:
            kommo_repo.update_lead_classification_cleared(conn, org["id"], lead_id)
            _audit(conn, org["id"], "kommo.lead_classification_cleared", {"lead_id": lead_id, "fields_cleared": len(clear_payload)})
        return {"status": "limpo", "lead_id": lead_id, "fields_cleared": len(clear_payload)}
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    finally:
        api.close()


def clear_classification_batch(slug: str, limit: int = 50) -> dict:
    """Limpa em lote os campos do Kommo para todos os leads que tiveram campos gravados."""
    with connect() as conn:
        org = _organization(conn, slug)
        lead_ids = kommo_repo.list_written_lead_ids(conn, org["id"], limit)
        if not lead_ids:
            return {"processed": 0, "fields_cleared": 0, "remaining": 0}
        api = _api(conn, org["id"])

    cleared = 0
    total_fields = 0
    try:
        specs = _cached_field_specs(api, org["id"])
        clear_payload = [{"field_id": spec.field_id, "values": []} for spec in specs]
        for lead_id in lead_ids:
            if clear_payload:
                api.request("PATCH", f"/api/v4/leads/{lead_id}", json={"custom_fields_values": clear_payload})
            with connect() as conn:
                kommo_repo.update_lead_classification_cleared(conn, org["id"], lead_id)
            cleared += 1
            total_fields += len(clear_payload)
        with connect() as conn:
            remaining = len(kommo_repo.list_written_lead_ids(conn, org["id"], 500))
            _audit(conn, org["id"], "kommo.batch_classification_cleared", {"processed": cleared, "remaining": remaining})
        return {"processed": cleared, "fields_cleared": total_fields, "remaining": remaining}
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    finally:
        api.close()


def classification_results(slug: str, page: int, page_size: int) -> dict:
    with connect() as conn:
        org = _organization(conn, slug)
        config = kommo_repo.get_config_public(conn, org["id"])
        summary = kommo_repo.classification_summary(conn, org["id"])
        rows = kommo_repo.list_lead_classifications(conn, org["id"], page_size, (page - 1) * page_size)
    labels = {key: label for key, label, _names in kommo_insights.DIMENSIONS}
    return {
        "subdomain": config["subdomain"] if config else None,
        "summary": {**dict(summary), **_engine_info()},
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "lead_id": row["lead_id"],
                "status": row["status"],
                "engine": row["engine"],
                "trigger": row["trigger"],
                "messages_count": row["messages_count"],
                "fields_written": row["fields_written"],
                "error": row["error"],
                "classified_at": row["classified_at"],
                "fields": [
                    {"key": key, "label": labels.get(key, key), **value} for key, value in (row["fields"] or {}).items()
                ],
            }
            for row in rows
        ],
    }


def classification_reset(slug: str) -> dict:
    """Limpa o histórico de classificações de teste para permitir início limpo."""
    with connect() as conn:
        org = _organization(conn, slug)
        deleted = kommo_repo.clear_lead_classifications(conn, org["id"])
        _audit(conn, org["id"], "kommo.classification_reset", {"deleted": deleted})
    return {"status": "ok", "deleted": deleted}


def test_classification(slug: str, text: str, phone: str | None = None) -> dict:

    """Testa a classificação sob demanda de um texto/mensagem arbitrária com a Laya AI e regras."""
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o texto para teste.")

    with connect() as conn:
        org = _organization(conn, slug)
        api = _api(conn, org["id"])

    try:
        specs = _cached_field_specs(api, org["id"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Não foi possível ler campos do Kommo para simulação: {str(exc)[:120]}",
        )
    finally:
        api.close()

    transcript = f"Cliente: {text}"
    customer_text = text

    decisions = lead_classifier.classify_with_rules(customer_text, phone, specs)
    engine = "regras"
    settings = get_settings()
    model_name = settings.decision_model_name or "multilingual"
    latency_ms: int | None = None
    model_error: str | None = None
    answers: dict[str, Any] = {}

    if settings.decision_model_api_key and transcript and specs:
        questions = lead_classifier.build_questions(specs)
        start = time.perf_counter()
        try:
            answers = lead_classifier.ask_decision_model(
                transcript,
                questions,
                settings.decision_model_url,
                settings.decision_model_api_key,
                model_name,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            model_decisions = lead_classifier.decisions_from_answers(answers, specs)
            decisions = lead_classifier.merge_decisions(model_decisions, decisions)
            engine = "modelo"
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            model_error = str(exc)[:200]

    labels = {key: label for key, label, _names in kommo_insights.DIMENSIONS}
    fields = [
        {
            "key": key,
            "label": labels.get(key, key),
            "values": item["values"],
            "confidence": item["confidence"],
            "source": item["source"],
        }
        for key, item in decisions.items()
    ]

    return {
        "status": "classificado" if decisions else "sem_sinal",
        "engine": engine,
        "model_name": model_name,
        "latency_ms": latency_ms,
        "model_error": model_error,
        "text": text,
        "phone": phone,
        "fields": fields,
        "raw_answers": answers,
    }


# --- Webhook: classificar a cada mensagem ou lead novo -------------------------


def webhook_enable(slug: str, api_base_url: str) -> dict:
    with connect() as conn:
        org = _organization(conn, slug)
        api = _api(conn, org["id"])
    secret = secrets.token_urlsafe(24)
    destination = f"{api_base_url.rstrip('/')}/portal-api/{slug}/kommo/webhook/{secret}"
    try:
        created = api.request("POST", "/api/v4/webhooks", json={"destination": destination, "settings": WEBHOOK_EVENTS})
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    finally:
        api.close()
    with connect() as conn:
        kommo_repo.upsert_webhook(conn, org["id"], secret, created.get("id"), destination, WEBHOOK_EVENTS)
        _audit(conn, org["id"], "kommo.webhook_enabled", {"events": WEBHOOK_EVENTS})
    return {"active": True, "events": WEBHOOK_EVENTS}


def webhook_lead_ids(form: dict[str, str]) -> set[int]:
    """Extrai os leads citados no corpo `x-www-form-urlencoded` do webhook do Kommo."""
    lead_ids: set[int] = set()
    for key, value in form.items():
        if not str(value).isdigit():
            continue
        if key.startswith("leads[add]") and key.endswith("[id]"):
            lead_ids.add(int(value))
        elif key.startswith("message[add]") and key.endswith(("[entity_id]", "[element_id]")):
            prefix = key.rsplit("[", 1)[0]
            entity_type = form.get(f"{prefix}[entity_type]") or form.get(f"{prefix}[element_type]") or ""
            # No webhook de mensagem o tipo vem como "lead" ou, no formato antigo, "2".
            if entity_type in ("lead", "leads", "2"):
                lead_ids.add(int(value))
    return lead_ids


def webhook_authorize(slug: str, secret: str) -> UUID:
    with connect() as conn:
        org = _organization(conn, slug)
        webhook = kommo_repo.get_webhook(conn, org["id"])
        if not webhook or not hmac.compare_digest(webhook["secret"], secret):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook desconhecido.")
        kommo_repo.touch_webhook(conn, org["id"])
    return org["id"]


def webhook_process(organization_id: UUID, lead_ids: set[int]) -> None:
    """Roda em segundo plano depois de responder 200 ao Kommo. Gera sugestões sem gravar direto."""
    if not lead_ids:
        return
    with connect() as conn:
        recent = set()
        for lead_id in lead_ids:
            row = kommo_repo.get_lead_classification(conn, organization_id, lead_id)
            # Se o lead estava aguardando o cliente detalhar, não bloqueia a reclassificação quando uma nova mensagem chegar
            if row and row.get("status") != "aguardando_cliente" and (time.time() - row["classified_at"].timestamp()) < _RECLASSIFY_AFTER_SECONDS:
                recent.add(lead_id)
        api = _api(conn, organization_id)
    try:
        specs = _field_specs(api)
        for lead_id in lead_ids - recent:
            # write=False: apenas classifica e sugere para confirmação humana, nunca sobrescreve o CRM sem aprovação
            _classify_and_store(organization_id, api, specs, lead_id, False, "webhook")
    except httpx.HTTPError:
        pass  # o lead continua na fila do histórico; nada a devolver para o Kommo
    finally:
        api.close()
