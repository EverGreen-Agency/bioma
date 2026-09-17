from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_platform_admin
from bioma_api.db import connect
from bioma_api.proposal_catalog import SERVICE_GROUPS
from bioma_api.proposal_documents import render_proposal_markdown, render_proposal_pdf
from bioma_api.repositories import projects as projects_repo
from bioma_api.repositories import proposal_lifecycle as lifecycle_repo
from bioma_api.repositories import proposal_translations as translations_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.projects import (
    ContractCreate,
    ProjectCreate,
    ProjectPlanGenerateRequest,
    ScopeItemCreate,
)
from bioma_api.schemas.proposal_lifecycle import (
    ProposalAcceptanceCreate,
    ProposalArchiveRequest,
    ProposalClaimsReview,
    ProposalCohort,
    ProposalCohortAnalytics,
    ProposalContentUpdate,
    ProposalConversion,
    ProposalConversionCreate,
    ProposalDelivery,
    ProposalDeliveryCreate,
    ProposalDetailResponse,
    ProposalEvent,
    ProposalLifecycleRecord,
    PublicProposalLifecycleRecord,
    ProposalRevisionCreate,
    ProposalStatusTransition,
)


ALLOWED_TRANSITIONS = {
    "draft": {"approved"},
    "approved": {"draft", "sent"},
    "sent": {"negotiating", "won", "lost"},
    "negotiating": {"won", "lost"},
    "won": set(),
    "lost": {"draft"},
}


def get_detail(proposal_id: UUID, user: CurrentUserResponse) -> ProposalDetailResponse:
    require_platform_admin(user)
    with connect() as conn:
        proposal = lifecycle_repo.get_proposal(conn, proposal_id)
        if not proposal or proposal["archived_at"] is not None:
            raise _not_found()
        if not proposal["content_markdown"]:
            proposal = lifecycle_repo.update_content(
                conn,
                proposal_id,
                render_proposal_markdown(dict(proposal)),
                proposal["claims"] or [],
            )
        revisions = lifecycle_repo.list_revisions(conn, proposal["series_id"])
        events = lifecycle_repo.list_events(conn, proposal_id)
        deliveries = lifecycle_repo.list_deliveries(conn, proposal_id)
        conversion = lifecycle_repo.find_conversion(conn, proposal_id)
    return ProposalDetailResponse(
        proposal=ProposalLifecycleRecord(**proposal),
        revisions=[ProposalLifecycleRecord(**row) for row in revisions],
        events=[ProposalEvent(**row) for row in events],
        deliveries=[ProposalDelivery(**row) for row in deliveries],
        conversion=ProposalConversion(**conversion) if conversion else None,
    )


def update_content(
    proposal_id: UUID,
    payload: ProposalContentUpdate,
    user: CurrentUserResponse,
) -> ProposalDetailResponse:
    require_platform_admin(user)
    with connect() as conn:
        proposal = _proposal(conn, proposal_id, for_update=True)
        if proposal["status"] != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conteúdo publicado não é editado em linha. Crie uma nova revisão.",
            )
        lifecycle_repo.update_content(
            conn,
            proposal_id,
            payload.content_markdown,
            [claim.model_dump() for claim in payload.claims],
        )
        lifecycle_repo.record_event(
            conn,
            proposal_id,
            "proposal.content_updated",
            user.id,
            {"claims_count": len(payload.claims)},
        )
        # É este o caminho que a tela de edição realmente usa (o `update_proposal`
        # de `services/proposals.py` é outro fluxo) — sem invalidar aqui, editar
        # o conteúdo pela tela não derrubaria a tradução em cache, e ela ficaria
        # mostrando o texto antigo como se fosse atual.
        translations_repo.invalidate(conn, proposal_id)
    return get_detail(proposal_id, user)


def review_claims(
    proposal_id: UUID,
    payload: ProposalClaimsReview,
    user: CurrentUserResponse,
) -> ProposalDetailResponse:
    require_platform_admin(user)
    with connect() as conn:
        proposal = _proposal(conn, proposal_id, for_update=True)
        if payload.status == "approved":
            unapproved = [claim for claim in proposal["claims"] if not claim.get("approved")]
            if unapproved:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Todas as alegações precisam de evidência e aprovação antes da liberação.",
                )
        lifecycle_repo.review_claims(conn, proposal_id, payload.status)
        lifecycle_repo.record_event(
            conn,
            proposal_id,
            f"proposal.claims_{payload.status}",
            user.id,
            {"note": payload.note},
        )
    return get_detail(proposal_id, user)


def transition_status(
    proposal_id: UUID,
    payload: ProposalStatusTransition,
    user: CurrentUserResponse,
) -> ProposalDetailResponse:
    require_platform_admin(user)
    with connect() as conn:
        proposal = _proposal(conn, proposal_id, for_update=True)
        current = proposal["status"]
        if payload.status not in ALLOWED_TRANSITIONS[current]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transição inválida: {current} → {payload.status}.",
            )
        if payload.status in {"approved", "sent"} and proposal["claims_review_status"] != "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Revise e aprove as alegações antes de aprovar ou enviar.",
            )
        lifecycle_repo.transition_status(conn, proposal_id, payload.status)
        lifecycle_repo.record_event(
            conn,
            proposal_id,
            f"proposal.status_{payload.status}",
            user.id,
            {"from": current, "reason": payload.reason},
        )
    return get_detail(proposal_id, user)


def create_revision(
    proposal_id: UUID,
    payload: ProposalRevisionCreate,
    user: CurrentUserResponse,
) -> ProposalDetailResponse:
    require_platform_admin(user)
    with connect() as conn:
        source = _proposal(conn, proposal_id)
        revision = lifecycle_repo.create_revision(conn, proposal_id)
        if not revision:
            raise _not_found()
        lifecycle_repo.record_event(
            conn,
            revision["id"],
            "proposal.revision_created",
            user.id,
            {"source_proposal_id": str(source["id"]), "reason": payload.reason},
        )
    return get_detail(revision["id"], user)


def archive(
    proposal_id: UUID,
    payload: ProposalArchiveRequest,
    user: CurrentUserResponse,
) -> None:
    require_platform_admin(user)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Confirmação obrigatória.")
    with connect() as conn:
        _proposal(conn, proposal_id, for_update=True)
        lifecycle_repo.record_event(
            conn,
            proposal_id,
            "proposal.archived",
            user.id,
            {"reason": payload.reason},
        )
        lifecycle_repo.archive_proposal(conn, proposal_id)


def create_delivery(
    proposal_id: UUID,
    payload: ProposalDeliveryCreate,
    user: CurrentUserResponse,
) -> ProposalDetailResponse:
    require_platform_admin(user)
    with connect() as conn:
        proposal = _proposal(conn, proposal_id, for_update=True)
        if proposal["claims_review_status"] != "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O envio exige revisão das alegações.",
            )
        if proposal["status"] not in {"approved", "sent", "negotiating"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A proposta precisa estar aprovada antes de preparar ou registrar um envio.",
            )
        if payload.channel == "signature_adapter" and (not payload.provider or not payload.external_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O adaptador de assinatura exige provedor e identificador externo.",
            )
        delivery = lifecycle_repo.create_delivery(
            conn,
            proposal_id,
            user.id,
            payload.model_dump(mode="json"),
        )
        lifecycle_repo.record_event(
            conn,
            proposal_id,
            "proposal.delivery_recorded",
            user.id,
            {
                "delivery_id": str(delivery["id"]),
                "channel": delivery["channel"],
                "status": delivery["status"],
            },
        )
    return get_detail(proposal_id, user)


def get_public_detail(public_token: str) -> PublicProposalLifecycleRecord:
    with connect() as conn:
        proposal = lifecycle_repo.get_public_proposal(conn, public_token, for_update=True)
        if not proposal:
            raise _not_found()
        proposal = lifecycle_repo.mark_viewed(conn, proposal["id"])
        lifecycle_repo.record_event(conn, proposal["id"], "proposal.viewed", None)
    return PublicProposalLifecycleRecord(**proposal)


def accept_public(
    public_token: str,
    payload: ProposalAcceptanceCreate,
) -> PublicProposalLifecycleRecord:
    with connect() as conn:
        proposal = lifecycle_repo.get_public_proposal(conn, public_token, for_update=True)
        if not proposal:
            raise _not_found()
        if proposal["claims_review_status"] != "approved" or proposal["status"] not in {"sent", "negotiating"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta proposta ainda não está liberada para aceite.",
            )
        updated = lifecycle_repo.record_acceptance(
            conn,
            proposal["id"],
            accepted=payload.accepted,
            signer_name=payload.signer_name,
            signer_email=str(payload.signer_email),
        )
        lifecycle_repo.record_event(
            conn,
            proposal["id"],
            "proposal.accepted" if payload.accepted else "proposal.rejected",
            None,
            {"signer_name": payload.signer_name, "signer_email": str(payload.signer_email)},
        )
    return PublicProposalLifecycleRecord(**updated)


def pdf_bytes(proposal_id: UUID, user: CurrentUserResponse) -> tuple[bytes, str]:
    detail = get_detail(proposal_id, user)
    proposal = detail.proposal
    if proposal.claims_review_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A exportação final exige revisão das alegações.",
        )
    filename = _safe_filename(proposal.title or proposal.client_name) + f"-v{proposal.version}.pdf"
    return render_proposal_pdf(proposal.model_dump()), filename


def convert_to_project(
    proposal_id: UUID,
    payload: ProposalConversionCreate,
    user: CurrentUserResponse,
) -> ProposalDetailResponse:
    require_platform_admin(user)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Confirmação HITL obrigatória.")
    conversion_for_plan = None
    proposal_for_plan = None
    with connect() as conn:
        proposal = _proposal(conn, proposal_id, for_update=True)
        existing = lifecycle_repo.find_conversion(conn, proposal_id)
        conversion_for_plan = existing
        proposal_for_plan = dict(proposal)
        if not existing:
            key_owner = lifecycle_repo.find_conversion_by_idempotency_key(conn, payload.idempotency_key)
            if key_owner:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A chave de idempotência já foi usada em outra conversão.",
                )
            if proposal["status"] != "won" or not proposal["workspace_id"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Somente proposta ganha e ligada a um cliente pode virar projeto.",
                )
            context = projects_repo.find_workspace_context(
                conn,
                proposal["workspace_id"],
                is_platform_admin(user),
                user.id,
            )
            if not context:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente ativo não encontrado.")
            project_payload = ProjectCreate(
                name=payload.project_name or proposal["title"],
                project_type=payload.project_type,
                status="planned",
                client_visible=True,
                objective=proposal["problem_summary"] or proposal["executive_summary"],
            )
            project = projects_repo.create_project(conn, context, user.id, project_payload.model_dump())
            contract_payload = ContractCreate(
                title=f"Contrato — {proposal['title']}",
                status="active" if proposal["acceptance_status"] == "accepted" else "draft",
                total_value=Decimal(proposal["pricing_cents"]) / Decimal("100") if proposal["pricing_cents"] else None,
                source_provider="bioma_proposal",
                external_id=str(proposal_id),
                signed_at=proposal["accepted_at"],
                client_visible=True,
            )
            contract = projects_repo.create_contract(conn, project["id"], user.id, contract_payload.model_dump())
            service_labels = _service_labels()
            for service_key in proposal["selected_services"]:
                scope_payload = ScopeItemCreate(
                    title=service_labels.get(service_key, service_key.replace("_", " ").title()),
                    description="Escopo originado da proposta comercial aprovada; critérios finais devem ser refinados no planejamento.",
                    acceptance_required=True,
                    acceptance_criteria="Entrega revisada pela EG e validada pelo cliente quando aplicável.",
                    client_visible=True,
                )
                projects_repo.create_scope_item(conn, contract["id"], scope_payload.model_dump())
            conversion = lifecycle_repo.insert_conversion(
                conn,
                proposal_id,
                payload.idempotency_key,
                project["id"],
                contract["id"],
                user.id,
            )
            projects_repo.write_audit(
                conn,
                user.id,
                context["subject_organization_id"],
                "proposal.converted_to_project",
                {
                    "proposal_id": str(proposal_id),
                    "project_id": str(project["id"]),
                    "contract_id": str(contract["id"]),
                    "conversion_id": str(conversion["id"]),
                },
            )
            lifecycle_repo.record_event(
                conn,
                proposal_id,
                "proposal.converted_to_project",
                user.id,
                {"project_id": str(project["id"]), "contract_id": str(contract["id"])},
            )
            conversion_for_plan = conversion
    if (
        payload.generate_plan_draft
        and conversion_for_plan
        and not conversion_for_plan["plan_id"]
        and proposal_for_plan
    ):
        _generate_conversion_plan_draft(
            proposal_id,
            conversion_for_plan,
            proposal_for_plan,
            user,
        )
    return get_detail(proposal_id, user)


def _generate_conversion_plan_draft(
    proposal_id: UUID,
    conversion,
    proposal: dict,
    user: CurrentUserResponse,
) -> None:
    # A geração usa outra transação: nenhuma chamada ao worker mantém locks comerciais abertos.
    from bioma_api.services import projects as project_service

    try:
        plan = project_service.generate_project_plan(
            conversion["project_id"],
            ProjectPlanGenerateRequest(
                contract_id=conversion["contract_id"],
                source_kind="contract",
                objective=proposal.get("problem_summary") or proposal.get("executive_summary"),
                briefing=proposal.get("content_markdown") or proposal.get("scope_offer"),
                technical_context=proposal.get("special_requirements"),
            ),
            user,
        )
    except HTTPException as exc:
        with connect() as conn:
            lifecycle_repo.record_event(
                conn,
                proposal_id,
                "proposal.plan_draft_failed",
                user.id,
                {"detail": str(exc.detail), "conversion_id": str(conversion["id"])},
            )
        return
    with connect() as conn:
        lifecycle_repo.attach_conversion_plan(conn, conversion["id"], plan.id)
        lifecycle_repo.record_event(
            conn,
            proposal_id,
            "proposal.plan_draft_created",
            user.id,
            {"plan_id": str(plan.id), "project_id": str(conversion["project_id"])},
        )


def cohort_analytics(user: CurrentUserResponse) -> ProposalCohortAnalytics:
    require_platform_admin(user)
    with connect() as conn:
        cohorts, medians = lifecycle_repo.cohort_analytics(conn)
    return ProposalCohortAnalytics(
        cohorts=[ProposalCohort(**row) for row in cohorts],
        median_days_to_first_send=medians["median_days_to_first_send"],
        median_days_to_close=medians["median_days_to_close"],
        generated_at=datetime.now(timezone.utc),
    )


def _proposal(conn, proposal_id: UUID, *, for_update: bool = False):
    proposal = lifecycle_repo.get_proposal(conn, proposal_id, for_update=for_update)
    if not proposal or proposal["archived_at"] is not None:
        raise _not_found()
    return proposal


def _service_labels() -> dict[str, str]:
    return {
        service["key"]: service["label"]
        for group in SERVICE_GROUPS
        for service in group["services"]
    }


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta não encontrada.")


def _safe_filename(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in normalized.split("-") if part)[:80] or "proposta"
