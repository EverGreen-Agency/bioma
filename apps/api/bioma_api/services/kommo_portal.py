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


def require_admin_key(authorization: str | None) -> None:
    settings = get_settings()
    expected = settings.portal_admin_key
    if not expected:
        if settings.app_env == "local":
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Portal EG sem chave configurada. Defina PORTAL_ADMIN_KEY no serviço da API.",
        )
    scheme, _, provided = (authorization or "").partition(" ")
    if scheme.lower() != "portal" or not hmac.compare_digest(provided.strip(), expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave do portal ausente ou inválida.")


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
    return kommo_crm._dashboard_response(snapshot, bool(config), config["subdomain"] if config else None, days)


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
    return {
        "organization": org["name"],
        "kommo": {
            "configured": bool(config),
            "subdomain": config["subdomain"] if config else None,
            "leads_count": snapshot["leads_count"] if snapshot else None,
            "fetched_at": snapshot["fetched_at"] if snapshot else None,
        },
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


def _lead_messages(api: KommoApi, lead_id: int) -> list[dict]:
    talks = (
        api.request(
            "GET", "/api/v4/talks", params={"filter[entity_id][]": lead_id, "filter[entity_type]": "lead", "limit": 50}
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
    messages = _lead_messages(api, lead_id)
    transcript, customer_text = lead_classifier.build_state(messages)
    phone = _contact_phone(api, lead)

    decisions = lead_classifier.classify_with_rules(customer_text, phone, specs)
    engine = "regras"
    settings = get_settings()
    if settings.decision_model_api_key and transcript:
        answers = lead_classifier.ask_decision_model(
            transcript,
            lead_classifier.build_questions(specs),
            settings.decision_model_url,
            settings.decision_model_api_key,
            settings.decision_model_name,
        )
        decisions = lead_classifier.merge_decisions(lead_classifier.decisions_from_answers(answers, specs), decisions)
        engine = "modelo"

    payload = lead_classifier.payload_for_kommo(decisions, specs, filled)
    if write and payload:
        api.request("PATCH", f"/api/v4/leads/{lead_id}", json={"custom_fields_values": payload})
    written_ids = {item["field_id"] for item in payload} if write else set()
    by_key = {spec.key: spec for spec in specs}
    fields = {
        key: {
            **decision,
            "already_filled": key in filled,
            "written": by_key[key].field_id in written_ids,
        }
        for key, decision in decisions.items()
    }
    return {
        "status": "classificado" if decisions else ("sem_conversa" if not transcript else "sem_sinal"),
        "engine": engine,
        "messages_count": len(messages),
        "fields": fields,
        "fields_written": len(written_ids),
    }


def _field_specs(api: KommoApi) -> list[lead_classifier.FieldSpec]:
    custom_fields = (
        api.request("GET", "/api/v4/leads/custom_fields", params={"limit": 250}).get("_embedded") or {}
    ).get("custom_fields") or []
    return lead_classifier.field_specs(custom_fields, _FIELD_TO_KEY)


def _classify_and_store(org_id: UUID, api: KommoApi, specs, lead_id: int, write: bool, trigger: str) -> dict:
    try:
        result = _classify_lead(api, specs, lead_id, write)
        error = None
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


def classify_batch(slug: str, limit: int, write: bool) -> dict:
    """Classifica os próximos `limit` leads do histórico que ainda não foram lidos."""
    with connect() as conn:
        org = _organization(conn, slug)
        snapshot = kommo_repo.get_crm_snapshot(conn, org["id"])
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Sincronize os leads do Kommo antes de classificar."
            )
        # Simular não consome a fila de gravação: o lead simulado volta a ser lido quando for para valer.
        done = kommo_repo.classified_lead_ids(conn, org["id"], include_simulated=not write)
        api = _api(conn, org["id"])

    # Mais recentes primeiro: é onde a classificação ainda muda o atendimento.
    queue = [lead["id"] for lead in sorted(snapshot["leads"], key=lambda item: -item["created_at"]) if lead["id"] not in done]
    batch = queue[:limit]
    written = 0
    classified = 0
    try:
        specs = _field_specs(api) if batch else []
        for lead_id in batch:
            result = _classify_and_store(org["id"], api, specs, lead_id, write, "historico" if write else "simulacao")
            written += result["fields_written"]
            classified += 1 if result["status"] == "classificado" else 0
    except httpx.HTTPError as exc:
        raise kommo_crm._kommo_error(exc) from exc
    finally:
        api.close()
    if batch:
        with connect() as conn:
            _audit(conn, org["id"], "kommo.leads_classified", {"leads": len(batch), "fields_written": written})
    return {
        "processed": len(batch),
        "classified": classified,
        "fields_written": written,
        "remaining": len(queue) - len(batch),
        "total": len(snapshot["leads"]),
    }


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
    """Roda em segundo plano depois de responder 200 ao Kommo."""
    if not lead_ids:
        return
    with connect() as conn:
        recent = set()
        for lead_id in lead_ids:
            row = kommo_repo.get_lead_classification(conn, organization_id, lead_id)
            if row and (time.time() - row["classified_at"].timestamp()) < _RECLASSIFY_AFTER_SECONDS:
                recent.add(lead_id)
        api = _api(conn, organization_id)
    try:
        specs = _field_specs(api)
        for lead_id in lead_ids - recent:
            _classify_and_store(organization_id, api, specs, lead_id, True, "webhook")
    except httpx.HTTPError:
        pass  # o lead continua na fila do histórico; nada a devolver para o Kommo
    finally:
        api.close()
