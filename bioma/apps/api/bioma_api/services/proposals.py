from typing import Any
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.model_pricing import cost_cents
from bioma_api.proposal_catalog import SERVICE_GROUPS, proposal_catalog
from bioma_api.proposal_documents import render_proposal_markdown
from bioma_api.repositories import proposal_lifecycle as proposal_lifecycle_repo
from bioma_api.repositories import proposal_translations as translations_repo
from bioma_api.repositories import proposals as proposals_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.proposals import (
    OpportunityCreatePayload,
    OpportunityContact,
    OpportunityContactCreate,
    OpportunityDetail,
    OpportunityIngestPayload,
    OpportunityPlatformSummary,
    OpportunityPlatformUpdate,
    OpportunitySummary,
    OpportunityUpdatePayload,
    CommercialActivity,
    CommercialActivityCreate,
    ProposalBriefCreatePayload,
    ProposalCreatePayload,
    ProposalSummary,
    ProposalTranslateRequest,
    ProposalTranslation,
    ProposalUpdatePayload,
    PublicProposalResponse,
)
from bioma_api.worker_bridge import execute_squad_pipeline_safe, translate_proposal_safe


def _require_admin(user: CurrentUserResponse) -> None:
    require_platform_admin(user)


def _run_proposal_squads(input_context: dict, user: CurrentUserResponse) -> tuple[dict, str]:
    pillar_results = {
        pillar: execute_squad_pipeline_safe(
            pilar=pillar,
            squad_key="growth_proposals",
            input_context=input_context,
            requested_by_user_id=str(user.id),
        )
        for pillar in ("oferta", "conversao", "demanda")
    }
    modes = {result["generation_mode"] for result in pillar_results.values()}
    return pillar_results, "live" if modes == {"live"} else "preview"


def _service_scope_items(selected_services: list[str]) -> list[dict]:
    labels = {
        service["key"]: {"label": service["label"], "group": group["label"]}
        for group in SERVICE_GROUPS
        for service in group["services"]
    }
    return [
        {"item": labels[key]["label"], "pilar": labels[key]["group"], "service_key": key}
        for key in selected_services
    ]


def get_proposal_catalog(user: CurrentUserResponse) -> dict:
    _require_admin(user)
    return proposal_catalog()


def list_opportunities(user: CurrentUserResponse, status_filter: str | None = None) -> list[OpportunitySummary]:
    _require_admin(user)
    with connect() as conn:
        rows = proposals_repo.list_opportunities(conn, status_filter=status_filter)
    return [OpportunitySummary(**r) for r in rows]


def list_platform_configs(user: CurrentUserResponse) -> list[OpportunityPlatformSummary]:
    _require_admin(user)
    with connect() as conn:
        rows = proposals_repo.list_platform_configs(conn)
    return [OpportunityPlatformSummary(**row) for row in rows]


def update_platform_config(
    platform_key: str,
    payload: OpportunityPlatformUpdate,
    user: CurrentUserResponse,
) -> OpportunityPlatformSummary:
    _require_admin(user)
    with connect() as conn:
        row = proposals_repo.upsert_platform_config(conn, platform_key, payload.model_dump(mode="json"))
    return OpportunityPlatformSummary(**row)


def list_freelancer_profiles(user: CurrentUserResponse) -> list[dict[str, Any]]:
    _require_admin(user)
    with connect() as conn:
        return proposals_repo.list_freelancer_profiles(conn)


def sync_and_audit_freelancer_profile(
    profile_url: str,
    platform_key: str | None,
    user: CurrentUserResponse,
) -> dict[str, Any]:
    _require_admin(user)
    from bioma_api.worker_bridge import _ensure_worker_in_path
    _ensure_worker_in_path()

    try:
        from bioma_worker.scrapers.profile_auditor import fetch_and_audit_profile_url
        audit_data = fetch_and_audit_profile_url(profile_url, platform_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível auditar o perfil informado.",
        ) from exc

    with connect() as conn:
        return proposals_repo.upsert_freelancer_profile(conn, audit_data)


def delete_freelancer_profile(profile_id: UUID, user: CurrentUserResponse) -> dict[str, str]:
    _require_admin(user)
    with connect() as conn:
        if not proposals_repo.delete_freelancer_profile(conn, profile_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado.")
    return {"status": "deleted"}




def ingest_opportunity(payload: OpportunityIngestPayload, user: CurrentUserResponse) -> OpportunitySummary:
    """Guarda a oportunidade como ela chegou. NÃO pontua.

    Havia aqui uma triagem por palavra-chave (base 50, +7 por termo de uma lista
    fixa, −10 por tecnologia de outra lista fixa) que produzia um número com cara
    de avaliação sem ser uma. Duas coisas estavam erradas: o número não media
    nada — "growth" no título valia o mesmo que "growth" como o serviço inteiro —
    e o gap vinha de sete termos escritos à mão, que nunca acompanhavam o que a
    EG de fato passou a saber fazer.

    Agora `fit_score` fica NULO até alguém pedir "Avaliar com IA". Nulo é
    "ninguém avaliou ainda", que é a verdade, e é diferente de zero.
    """
    _require_admin(user)
    with connect() as conn:
        existing = proposals_repo.find_existing_opportunity(conn, payload.url, payload.source_platform, payload.title)
        if existing:
            return OpportunitySummary(**existing)

        created = proposals_repo.create_opportunity(
            conn,
            {
                "workspace_id": payload.workspace_id,
                "owner_user_id": payload.owner_user_id or user.id,
                "source_platform": payload.source_platform,
                "title": payload.title,
                "url": payload.url,
                "description": payload.description,
                "budget_text": payload.budget_text,
                "fit_score": None,
                "fit_analysis": None,
                "status": "new",
                "raw_payload": payload.raw_payload,
            },
        )
        proposals_repo.create_commercial_activity(
            conn,
            created["id"],
            {
                "activity_type": "captured",
                "title": "Oportunidade capturada",
                "body": payload.description,
                "source_kind": payload.source_platform,
                "source_ref": payload.url,
                "idempotency_key": f"capture:{created['id']}",
                "metadata": {"external_id": payload.raw_payload.get("external_id")},
            },
            user.id,
        )
        return OpportunitySummary(**created)


def get_opportunity_detail(opportunity_id: UUID, user: CurrentUserResponse) -> OpportunityDetail:
    _require_admin(user)
    with connect() as conn:
        row = proposals_repo.get_opportunity(conn, opportunity_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")
        activities = proposals_repo.list_commercial_activities(conn, opportunity_id)
        contacts = proposals_repo.list_opportunity_contacts(conn, opportunity_id)
    return OpportunityDetail(
        opportunity=OpportunitySummary(**row),
        activities=[CommercialActivity(**activity) for activity in activities],
        contacts=[OpportunityContact(**contact) for contact in contacts],
    )


def update_opportunity(
    opportunity_id: UUID, payload: OpportunityUpdatePayload, user: CurrentUserResponse
) -> OpportunityDetail:
    _require_admin(user)
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        current = proposals_repo.get_opportunity(conn, opportunity_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")
        if updates.get("status") in {"won", "lost", "rejected", "archived"}:
            updates["closed_at"] = datetime.now(timezone.utc)
        elif "status" in updates:
            updates["closed_at"] = None
        row = proposals_repo.update_opportunity(conn, opportunity_id, updates)
        if "status" in updates and updates["status"] != current["status"]:
            activity_type = updates["status"] if updates["status"] in {"won", "lost"} else "status_changed"
            proposals_repo.create_commercial_activity(
                conn,
                opportunity_id,
                {
                    "activity_type": activity_type,
                    "title": f"Status alterado para {updates['status']}",
                    "source_kind": "bioma",
                    "metadata": {"from": current["status"], "to": updates["status"]},
                },
                user.id,
            )
    assert row is not None
    return get_opportunity_detail(opportunity_id, user)


def add_commercial_activity(
    opportunity_id: UUID, payload: CommercialActivityCreate, user: CurrentUserResponse
) -> OpportunityDetail:
    _require_admin(user)
    with connect() as conn:
        if not proposals_repo.get_opportunity(conn, opportunity_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")
        proposals_repo.create_commercial_activity(conn, opportunity_id, payload.model_dump(), user.id)
    return get_opportunity_detail(opportunity_id, user)


def add_opportunity_contact(
    opportunity_id: UUID, payload: OpportunityContactCreate, user: CurrentUserResponse
) -> OpportunityDetail:
    _require_admin(user)
    with connect() as conn:
        if not proposals_repo.get_opportunity(conn, opportunity_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")
        lead = conn.execute("select id from leads where id = %s", (payload.lead_id,)).fetchone()
        if not lead:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lead não encontrado.")
        proposals_repo.add_opportunity_contact(conn, opportunity_id, payload.model_dump(), user.id)
    return get_opportunity_detail(opportunity_id, user)


def agency_skills_inventory(conn) -> list[dict[str, str]]:
    """O que a EG sabe fazer, com a evidência de onde isso está registrado.

    Antes o inventário era só `tech_skill_inventory` — sete linhas digitadas à
    mão que ninguém reabastecia. Um gap detectado contra essa lista dizia mais
    sobre a lista estar desatualizada do que sobre a EG não saber fazer.

    Agora é a união de três fontes que se mantêm sozinhas conforme a operação
    acontece, e cada item carrega de onde veio — para o gap ser discutível
    ("isso é gap mesmo ou o radar que está velho?") em vez de um veredito cego:

    - Tech Radar (`eg_stack_techs`, anéis adopt/trial): decisão técnica tomada e
      registrada em ADR. É a fonte mais forte, e já é editável pelo produto.
    - Inventário comercial (`tech_skill_inventory`): o que a EG vende, que nem
      sempre é uma tecnologia (ex.: "Landing Pages de Alta Conversão").
    - Projetos concluídos: entrega feita é a evidência mais dura que existe.

    Ainda não deriva competência de dentro das tarefas — o volume de projetos
    concluídos é pequeno demais para isso significar algo hoje. Quando crescer,
    é aqui que entra.
    """
    inventory: dict[str, dict[str, str]] = {}

    def add(name: str | None, evidence: str) -> None:
        clean = (name or "").strip()
        if not clean:
            return
        # Primeira evidência ganha: as fontes estão em ordem de força.
        inventory.setdefault(clean.lower(), {"skill": clean, "evidence": evidence})

    for row in proposals_repo.list_adopted_stack_techs(conn):
        add(row["name"], f"Tech Radar · anel {row['ring']}" + (f" · {row['adr']}" if row.get("adr") else ""))
    for row in proposals_repo.list_tech_skills(conn):
        if row.get("status") == "available":
            add(row["skill_name"], "Inventário comercial da EG")
    for row in proposals_repo.list_completed_project_types(conn):
        add(row["label"], f"{row['count']} projeto(s) concluído(s) deste tipo")

    return sorted(inventory.values(), key=lambda item: item["skill"].lower())


def evaluate_opportunity_with_ai(opp_id: UUID, user: CurrentUserResponse) -> OpportunitySummary:
    _require_admin(user)
    with connect() as conn:
        opp = proposals_repo.get_opportunity(conn, opp_id)
        if not opp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")

        inventory = agency_skills_inventory(conn)
        freelancers = [f.get("display_name") for f in proposals_repo.list_freelancer_profiles(conn)]

    input_context = {
        "opportunity_title": opp["title"],
        "opportunity_description": opp.get("description") or "Sem descrição detalhada",
        "budget_text": opp.get("budget_text") or "A combinar",
        "source_platform": opp["source_platform"],
        # Vai com a evidência junto: o modelo precisa saber que "React 19" está no
        # anel adopt do radar, não que alguém digitou "react" numa lista.
        "agency_skills_inventory": inventory,
        "team_profiles": freelancers,
    }

    try:
        squad_result = execute_squad_pipeline_safe(
            pilar="opportunity_fit",
            squad_key="opportunity_fit_scoring",
            input_context=input_context,
            requested_by_user_id=str(user.id),
        )
    except Exception as exc:
        # Falha real do pipeline (worker fora do ar, bug, provedor indisponível
        # com chave configurada) precisa aparecer como erro — nunca virar um
        # número inventado disfarçado de avaliação de IA bem-sucedida.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível avaliar a oportunidade agora. Tente novamente em instantes.",
        ) from exc

    output = squad_result["output_data"]
    generation_mode = squad_result.get("generation_mode", "live")
    ai_score = output["fit_score"]
    label = "🤖 IA" if generation_mode == "live" else "🧮 Prévia local"
    ai_analysis = f"{label}: {output['fit_analysis']}"

    with connect() as conn:
        updated = proposals_repo.update_opportunity_status(
            conn, opp_id, status_val="qualified" if ai_score >= 70 else opp["status"],
            fit_score=ai_score, fit_analysis=ai_analysis,
        )
        # Gap agora nasce da avaliação, não de uma lista fixa de sete termos:
        # o modelo comparou a vaga com o inventário com evidência e disse o que
        # falta. Sem duplicar o que já está aberto para a mesma oportunidade.
        already_open = {
            row["missing_skill"].strip().lower()
            for row in proposals_repo.list_skill_gaps(conn)
            if str(row.get("opportunity_id")) == str(opp_id)
        }
        for missing in output.get("skill_gaps") or []:
            clean = str(missing).strip()
            if clean and clean.lower() not in already_open:
                proposals_repo.create_skill_gap(conn, opp_id, clean, opp["title"], opp.get("url"))
                already_open.add(clean.lower())
    return OpportunitySummary(**updated)


def sync_opportunities_from_scrapers(user: CurrentUserResponse) -> dict[str, Any]:
    _require_admin(user)
    from bioma_api.worker_bridge import _ensure_worker_in_path
    _ensure_worker_in_path()

    custom_sources = []
    with connect() as conn:
        configs = proposals_repo.list_platform_configs(conn)
        for cfg in configs:
            rss_url = cfg.get("rss_url")
            if rss_url and rss_url.strip():
                custom_sources.append({
                    "platform": cfg["platform_key"],
                    "name": cfg["platform_name"],
                    "url": rss_url.strip(),
                })

    try:
        from bioma_worker.scrapers.opportunities import fetch_rss_opportunities
        items = fetch_rss_opportunities(custom_sources=custom_sources)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O radar não conseguiu carregar as fontes configuradas.",
        ) from exc
    new_count = 0
    skipped_count = 0

    with connect() as conn:
        for item in items:
            existing = proposals_repo.find_existing_opportunity(conn, item.get("url"), item["source_platform"], item["title"])
            if existing:
                skipped_count += 1
            else:
                payload = OpportunityIngestPayload(
                    source_platform=item["source_platform"],
                    title=item["title"],
                    url=item.get("url"),
                    description=item.get("description"),
                    budget_text=item.get("budget_text"),
                    raw_payload=item.get("raw_payload", {}),
                )
                ingest_opportunity(payload, user)
                new_count += 1

    return {
        "status": "completed",
        "scanned": len(items),
        "new": new_count,
        "skipped": skipped_count,
    }



def generate_proposal_for_opportunity(opp_id: UUID, user: CurrentUserResponse) -> ProposalSummary:
    _require_admin(user)
    with connect() as conn:
        opp = proposals_repo.get_opportunity(conn, opp_id)
        if not opp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")

    input_context = {
        "objective": opp["title"],
        "project_title": opp["title"],
        "project_description": opp.get("description", ""),
        "budget_text": opp.get("budget_text", ""),
        "source": opp["source_platform"],
    }
    pillar_results, generation_mode = _run_proposal_squads(input_context, user)
    oferta = pillar_results["oferta"]["output_data"]
    conversao = pillar_results["conversao"]["output_data"]
    demanda = pillar_results["demanda"]["output_data"]
    title = opp["title"]

    proposal_payload = {
            "opportunity_id": str(opp_id),
            "client_name": f"Projeto: {title[:40]}",
            "target_niche": opp["source_platform"].capitalize(),
            "executive_summary": oferta["headline"],
            "scope_offer": oferta["mecanismo_unico"],
            "scope_conversion": conversao["script_fechamento"],
            "scope_demand": demanda["estrutura_campanha"],
            "scope_items": [
                {"item": oferta["headline"], "pilar": "Oferta", "details": oferta},
                {"item": conversao["script_fechamento"], "pilar": "Conversão", "details": conversao},
                {"item": demanda["estrutura_campanha"], "pilar": "Demanda", "details": demanda},
            ],
            "attached_cases": [],
            "pricing_cents": 0,
            "delivery_days": 0,
            "status": "draft",
            "generation_mode": generation_mode,
        }

    proposal_payload["content_markdown"] = render_proposal_markdown(proposal_payload)
    with connect() as conn:
        proposal = proposals_repo.create_proposal(conn, proposal_payload, user_id=user.id)
        proposals_repo.update_opportunity_status(conn, opp_id, status_val="proposal_generated")
        proposals_repo.create_commercial_activity(
            conn,
            opp_id,
            {
                "activity_type": "proposal_created",
                "title": proposal.get("title") or f"Proposta para {title}",
                "source_kind": "commercial_proposal",
                "source_ref": str(proposal["id"]),
                "idempotency_key": f"proposal-created:{proposal['id']}",
                "metadata": {"proposal_id": str(proposal["id"]), "generation_mode": generation_mode},
            },
            user.id,
        )

    return ProposalSummary(**proposal)


def list_proposals(user: CurrentUserResponse) -> list[ProposalSummary]:
    _require_admin(user)
    with connect() as conn:
        rows = proposals_repo.list_proposals(conn)
    return [ProposalSummary(**r) for r in rows]


def create_proposal(payload: ProposalCreatePayload, user: CurrentUserResponse) -> ProposalSummary:
    _require_admin(user)
    data = payload.model_dump()
    data["content_markdown"] = render_proposal_markdown(data)
    with connect() as conn:
        row = proposals_repo.create_proposal(conn, data, user_id=user.id)
    return ProposalSummary(**row)


def generate_proposal_from_brief(
    payload: ProposalBriefCreatePayload,
    user: CurrentUserResponse,
) -> ProposalSummary:
    _require_admin(user)
    with connect() as conn:
        client = proposals_repo.get_workspace_proposal_context(conn, payload.workspace_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente ativo não encontrado.",
            )

    brief = payload.model_dump(mode="json")
    client_context = {
        key: str(value) if isinstance(value, UUID) else value
        for key, value in client.items()
        if key not in {"tenant_organization_id", "subject_organization_id"} and value is not None
    }
    input_context = {
        "objective": payload.problem_summary,
        "project_title": payload.title,
        "project_description": payload.additional_context or payload.problem_summary,
        "budget_text": payload.estimated_budget,
        "source": "bioma_commercial_brief",
        "commercial_brief": brief,
        "client_context": client_context,
    }
    pillar_results, generation_mode = _run_proposal_squads(input_context, user)
    oferta = pillar_results["oferta"]["output_data"]
    conversao = pillar_results["conversao"]["output_data"]
    demanda = pillar_results["demanda"]["output_data"]

    generated_items = [
        {
            "item": oferta.get("headline", payload.title),
            "pilar": "Oferta",
            "details": oferta,
        },
        {
            "item": conversao.get("script_fechamento", "Estratégia comercial"),
            "pilar": "Conversão",
            "details": conversao,
        },
        {
            "item": demanda.get("estrutura_campanha", "Estratégia de demanda"),
            "pilar": "Demanda",
            "details": demanda,
        },
    ]
    proposal_payload = {
        "workspace_id": str(payload.workspace_id),
        "title": payload.title,
        "client_name": client["organization_name"],
        "target_niche": client.get("sector"),
        "executive_summary": oferta.get("headline", payload.problem_summary),
        "scope_offer": oferta.get("mecanismo_unico"),
        "scope_conversion": conversao.get("script_fechamento"),
        "scope_demand": demanda.get("estrutura_campanha"),
        "scope_items": _service_scope_items(payload.selected_services) + generated_items,
        "attached_cases": [],
        "pricing_cents": 0,
        "delivery_days": 0,
        "status": "draft",
        "generation_mode": generation_mode,
        **brief,
        "intake_snapshot": {
            "schema_key": "commercial_proposal_v1",
            "schema_version": 1,
            "brief": brief,
            "client_context": client_context,
        },
    }
    proposal_payload["content_markdown"] = render_proposal_markdown(proposal_payload)
    with connect() as conn:
        row = proposals_repo.create_proposal(conn, proposal_payload, user_id=user.id)
    return ProposalSummary(**row)


def update_proposal(proposal_id: UUID, payload: ProposalUpdatePayload, user: CurrentUserResponse) -> ProposalSummary:
    _require_admin(user)
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Use a transição auditada do ciclo de vida para alterar o status.",
        )
    with connect() as conn:
        row = proposals_repo.update_proposal(conn, proposal_id, updates)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta não encontrada.")
        # Editar o original invalida TODO o cache de tradução — tradução
        # desatualizada lida como se fosse atual é pior que reprocessar.
        translations_repo.invalidate(conn, proposal_id)
    return ProposalSummary(**row)


def translate_proposal(proposal_id: UUID, payload: ProposalTranslateRequest, user: CurrentUserResponse) -> ProposalTranslation:
    """Primeira leitura naquele idioma traduz e guarda; da segunda em diante é
    leitura de banco. `update_proposal` apaga o cache quando o original muda."""
    _require_admin(user)
    with connect() as conn:
        proposal = proposal_lifecycle_repo.get_proposal(conn, proposal_id)
        if not proposal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta não encontrada.")

        cached = translations_repo.get_cached(conn, proposal_id, payload.language)
        if cached:
            return ProposalTranslation(**cached)

    content_markdown = proposal.get("content_markdown") or render_proposal_markdown(proposal)
    try:
        result = translate_proposal_safe(
            {
                "title": proposal.get("title") or proposal["client_name"],
                "content_markdown": content_markdown,
                "target_language": payload.language,
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível traduzir agora. Tente novamente em instantes.",
        ) from exc

    output = result["output"]
    usage = result.get("usage") or {}
    with connect() as conn:
        saved = translations_repo.save(
            conn,
            {
                "proposal_id": proposal_id,
                "language": payload.language,
                "title": output["title"],
                "content_markdown": output["content_markdown"],
                "generation_mode": result["generation_mode"],
                "provider": result.get("provider"),
                "model": result.get("model"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "cost_cents": cost_cents(result.get("model"), usage.get("input_tokens"), usage.get("output_tokens")),
                "created_by": user.id,
            },
        )
    return ProposalTranslation(**saved)


def get_public_proposal(public_token: str) -> PublicProposalResponse:
    with connect() as conn:
        row = proposals_repo.get_proposal_by_public_token(conn, public_token)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta comercial não encontrada ou expirada.")
    return PublicProposalResponse(**row)


def list_tech_skills(user: CurrentUserResponse) -> list[dict[str, Any]]:
    _require_admin(user)
    with connect() as conn:
        return proposals_repo.list_tech_skills(conn)


def list_skill_gaps(user: CurrentUserResponse) -> list[dict[str, Any]]:
    _require_admin(user)
    with connect() as conn:
        return proposals_repo.list_skill_gaps(conn)


def resolve_skill_gap(gap_id: UUID, user: CurrentUserResponse) -> dict[str, Any]:
    _require_admin(user)
    with connect() as conn:
        row = proposals_repo.resolve_skill_gap(conn, gap_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gap não encontrado.")
        return row


def get_proposal_analytics(user: CurrentUserResponse) -> dict[str, Any]:
    _require_admin(user)
    with connect() as conn:
        return proposals_repo.get_proposal_analytics_metrics(conn)
