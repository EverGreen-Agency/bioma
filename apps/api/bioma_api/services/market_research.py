from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError

from bioma_api.access import (
    is_platform_admin,
    resolve_accessible_client,
)
from bioma_api.db import connect
from bioma_api.repositories import ai_operations as ai_operations_repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import market_research as research_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.market_research import (
    MarketResearchCreate,
    MarketResearchDetail,
    MarketResearchRefineRequest,
    MarketResearchRefinement,
    MarketResearchReport,
    MarketResearchSummary,
)
from bioma_api.worker_bridge import (
    generate_market_research_safe,
    refine_market_sector_safe,
)


def list_researches(workspace_id: UUID, user: CurrentUserResponse) -> list[MarketResearchSummary]:
    with connect() as conn:
        workspace = _workspace(conn, workspace_id, user, "view")
        rows = research_repo.list_researches(
            conn,
            workspace["workspace_id"],
            is_platform_admin(user),
            user.id,
        )
    return [MarketResearchSummary(**row) for row in rows]


def get_research(research_id: UUID, user: CurrentUserResponse) -> MarketResearchDetail:
    with connect() as conn:
        row = _research(conn, research_id, user)
        sources = research_repo.list_sources(conn, research_id)
    return MarketResearchDetail(**row, sources=sources)


def refine_sector(
    workspace_id: UUID,
    payload: MarketResearchRefineRequest,
    user: CurrentUserResponse,
) -> MarketResearchRefinement:
    with connect() as conn:
        workspace = _workspace(conn, workspace_id, user, "manage_work")
        resolved_workspace_id = workspace["workspace_id"]
        tenant_organization_id = workspace["tenant_organization_id"]
        subject_organization_id = workspace["organization_id"]

    # O provedor nunca mantém uma transação do Postgres aberta.
    result = refine_market_sector_safe(payload.model_dump())
    try:
        refinement = MarketResearchRefinement.model_validate(
            {**result["output"], "generation_mode": result["generation_mode"]}
        )
    except (KeyError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O refinamento do setor retornou uma estrutura inválida.",
        ) from exc

    with connect() as conn:
        _record_usage(
            conn,
            tenant_organization_id,
            resolved_workspace_id,
            user.id,
            result,
            source="market_research_refinement",
            external_event_id=result.get("response_id"),
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            subject_organization_id,
            "market_research.sector_refined",
            {
                "workspace_id": str(resolved_workspace_id),
                "sector": payload.sector,
                "generation_mode": result["generation_mode"],
            },
        )
    return refinement


def create_research(
    workspace_id: UUID,
    payload: MarketResearchCreate,
    user: CurrentUserResponse,
) -> MarketResearchDetail:
    request_data = payload.model_dump(mode="json")
    with connect() as conn:
        workspace = _workspace(conn, workspace_id, user, "manage_work")
        resolved_workspace_id = workspace["workspace_id"]
        tenant_organization_id = workspace["tenant_organization_id"]
        subject_organization_id = workspace["organization_id"]
        research_repo.lock_workspace(conn, resolved_workspace_id)
        version = research_repo.next_version(conn, resolved_workspace_id)
        research = research_repo.create_running(
            conn,
            resolved_workspace_id,
            tenant_organization_id,
            subject_organization_id,
            user.id,
            version,
            request_data,
        )
        research_id = research["id"]
        client_hub_repo.write_audit(
            conn,
            user.id,
            subject_organization_id,
            "market_research.started",
            {
                "workspace_id": str(resolved_workspace_id),
                "research_id": str(research_id),
                "version": version,
                "sector": payload.sector,
            },
        )

    try:
        # Pesquisa web e inferência ocorrem fora da transação.
        result = generate_market_research_safe(request_data)
        report = MarketResearchReport.model_validate(result["report"])
        sources = [source.model_dump(mode="json") for source in report.sources]
        if result["generation_mode"] == "live" and len(sources) < 3:
            raise ValueError("Pesquisa live retornou menos de três fontes verificáveis.")
        normalized_result = {
            **result,
            "report": report.model_dump(mode="json"),
            "sources": sources,
        }
    except Exception as exc:
        with connect() as conn:
            research_repo.fail_research(conn, research_id, str(exc))
            client_hub_repo.write_audit(
                conn,
                user.id,
                subject_organization_id,
                "market_research.failed",
                {
                    "workspace_id": str(resolved_workspace_id),
                    "research_id": str(research_id),
                    "version": version,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A pesquisa não pôde ser concluída. O rascunho foi preservado como falha auditável.",
        ) from exc

    with connect() as conn:
        research_repo.replace_sources(conn, research_id, normalized_result["sources"])
        completed = research_repo.complete_research(conn, research_id, normalized_result)
        if not completed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pesquisa mudou de estado antes da conclusão.",
            )
        _record_usage(
            conn,
            tenant_organization_id,
            resolved_workspace_id,
            user.id,
            normalized_result,
            source="market_research",
            external_event_id=str(research_id),
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            subject_organization_id,
            "market_research.completed",
            {
                "workspace_id": str(resolved_workspace_id),
                "research_id": str(research_id),
                "version": version,
                "generation_mode": normalized_result["generation_mode"],
                "source_count": len(normalized_result["sources"]),
            },
        )
    return get_research(research_id, user)


def _workspace(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str):
    workspace = resolve_accessible_client(
        conn,
        workspace_id,
        user,
        module="hub",
        capability=capability,
    )
    if workspace["workspace_kind"] != "agency_internal":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesquisa de mercado não encontrada.")
    return workspace


def _research(conn, research_id: UUID, user: CurrentUserResponse):
    row = research_repo.find_research_context(conn, research_id, is_platform_admin(user), user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesquisa não encontrada.")
    return row


def _record_usage(
    conn,
    tenant_organization_id: UUID,
    workspace_id: UUID,
    user_id: UUID,
    result: dict,
    *,
    source: str,
    external_event_id: str | None,
) -> None:
    usage = result.get("token_usage") or {}
    if result.get("generation_mode") == "preview" and not usage.get("total_tokens"):
        return
    ai_operations_repo.create_usage_event(
        conn,
        tenant_organization_id,
        user_id,
        {
            "workspace_id": workspace_id,
            "provider": result.get("provider") or "unknown",
            "model": result.get("model"),
            "source": source,
            "external_event_id": external_event_id,
            "input_units": usage.get("prompt_tokens"),
            "output_units": usage.get("completion_tokens"),
            "cached_units": 0,
            "unit": "tokens",
            "cost_cents": result.get("estimated_cost_cents"),
            "currency": "USD",
            "metadata": {
                "total_tokens": usage.get("total_tokens", 0),
                "cost_status": (
                    "known" if result.get("estimated_cost_cents") is not None else "unknown"
                ),
            },
        },
    )
