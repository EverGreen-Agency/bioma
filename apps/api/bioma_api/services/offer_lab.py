from uuid import UUID
from fastapi import HTTPException, status

from bioma_api.access import resolve_accessible_client
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import offer_lab as offer_lab_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.offer_lab import (
    BoardVerdict,
    OfferBonus,
    OfferEvaluatePayload,
    OfferStack,
    OfferValidationResponse,
    ProblemSolutionItem,
    RiskReversalGuarantee,
    ValueEquation,
)


def calculate_value_score(ve: ValueEquation) -> float:
    """Calcula a pontuação da Equação de Valor de Alex Hormozi ($100M Offers).

    Score = (Dream Outcome * Perceived Likelihood) / (Time Delay * Effort & Sacrifice)
    Escala: de 0.00 até 100.00
    """
    numerator = ve.dream_outcome * ve.perceived_likelihood
    denominator = max(1.0, ve.time_delay * ve.effort_and_sacrifice)
    score = numerator / denominator
    return round(score, 2)


def generate_board_verdict(
    product: str,
    audience: str,
    price_cents: int,
    ve: ValueEquation,
    problems: list[ProblemSolutionItem],
    stack: OfferStack | None,
) -> BoardVerdict:
    """Gera o parecer consultivo do conselho virtual (Hormozi, Thiel, Jobs)."""
    score = calculate_value_score(ve)
    dealbreakers: list[str] = []

    # 1. Parecer Alex Hormozi ($100M Offers)
    hormozi_score = min(10.0, round(score / 1.5, 1))
    if ve.effort_and_sacrifice >= 7.0:
        dealbreakers.append("Esforço e atrito exigidos do cliente são muito altos (deve incluir mais 'Done-For-You' ou templates prontos).")
    if ve.perceived_likelihood <= 4.0:
        dealbreakers.append("Certeza percebida baixa: ausência de garantia forte de reversão de risco ou provas sociais consistentes.")

    hormozi_verdict = (
        f"Score de Valor: {score}/100. "
        + ("Excelente arquitetura de oferta irrecusável com alto valor percebido." if score >= 12.0
           else "Oferta com margem de melhoria. Empilhe bônus estratégicos que resolvam a próxima dúvida do comprador e inverta o risco com garantia incondicional ou condicional clara.")
    )

    # 2. Parecer Peter Thiel (Zero to One - Diferenciação & Monopólio)
    thiel_score = round(min(10.0, max(1.0, (ve.dream_outcome * 0.7) + (10 - ve.effort_and_sacrifice) * 0.3)), 1)
    if thiel_score < 5.0:
        dealbreakers.append("Risco de comoditização: a promessa parece similar a concorrentes tradicionais (não é 10x melhor em nenhum eixo).")
    thiel_verdict = (
        "Posicionamento focado em monopólio de nicho." if thiel_score >= 7.0
        else "Perigo de competição destrutiva: busque um segredo do nicho ou uma vantagem proprietária em dados/processo para fugir da comparação direta de preço."
    )

    # 3. Parecer Steve Jobs (Foco no Essencial e Experiência do Produto)
    jobs_score = round(min(10.0, max(1.0, (11 - ve.time_delay) * 0.6 + (11 - ve.effort_and_sacrifice) * 0.4)), 1)
    if ve.time_delay >= 7.0:
        dealbreakers.append("Demora para o primeiro valor (Time-to-Value excessivo). O cliente precisa ter uma vitória rápida nas primeiras 48h.")
    jobs_verdict = (
        "Experiência limpa, atrito reduzido e foco no resultado primário." if jobs_score >= 7.0
        else "Complexidade em excesso: elimine passos desnecessários no onboarding e entregue o primeiro 'uau' imediatamente."
    )

    recommendation = "proceed" if len(dealbreakers) == 0 and score >= 10.0 else "refine_offer" if score >= 5.0 else "abort"

    return BoardVerdict(
        hormozi_offers_score=hormozi_score,
        hormozi_verdict=hormozi_verdict,
        thiel_monopoly_score=thiel_score,
        thiel_verdict=thiel_verdict,
        jobs_product_score=jobs_score,
        jobs_verdict=jobs_verdict,
        dealbreakers=dealbreakers,
        overall_recommendation=recommendation,
    )


def evaluate_offer_preview(payload: OfferEvaluatePayload) -> dict:
    """Avaliação em tempo real (Stateless) para simulador no navegador."""
    score = calculate_value_score(payload.value_equation)

    stack = payload.offer_stack or OfferStack(
        core_offer_name=payload.product_or_service,
        core_offer_description=f"Solução para {payload.target_audience}",
        magic_name=f"Acelerador de Resultados para {payload.target_audience}",
        bonuses=[],
        guarantee=RiskReversalGuarantee(
            type="conditional",
            title="Garantia de Execução Alinhada",
            terms="Se em 60 dias o escopo acordado for cumprido e a meta não for atingida, trabalhamos de graça até atingir.",
            conditions=["Comparecer aos alinhamentos quinzenais", "Executar os acessos em até 48h"],
        ),
        scarcity_urgency="Limite de 3 novos projetos por mês para garantir dedicação do time sênior.",
    )

    verdict = generate_board_verdict(
        product=payload.product_or_service,
        audience=payload.target_audience,
        price_cents=payload.current_price_cents,
        ve=payload.value_equation,
        problems=payload.problems_and_solutions,
        stack=stack,
    )

    return {
        "value_score": score,
        "offer_stack": stack,
        "board_verdict": verdict,
    }


def list_workspace_validations(workspace_id: UUID, user: CurrentUserResponse) -> list[OfferValidationResponse]:
    with connect() as conn:
        workspace = resolve_accessible_client(
            conn,
            workspace_id,
            user,
            module="hub",
            capability="view",
            require_kind="client",
        )
        rows = offer_lab_repo.list_validations(conn, workspace["workspace_id"])
        return [_map_response(row) for row in rows]


def get_workspace_validation(
    workspace_id: UUID,
    validation_id: UUID,
    user: CurrentUserResponse,
) -> OfferValidationResponse:
    with connect() as conn:
        workspace = resolve_accessible_client(
            conn,
            workspace_id,
            user,
            module="hub",
            capability="view",
            require_kind="client",
        )
        row = offer_lab_repo.get_validation(conn, validation_id, workspace["workspace_id"])
        if not row:
            raise HTTPException(status_code=404, detail="Validação de oferta não encontrada.")
        return _map_response(row)


def create_workspace_validation(
    workspace_id: UUID,
    payload: OfferEvaluatePayload,
    user: CurrentUserResponse,
) -> OfferValidationResponse:
    with connect() as conn:
        workspace = resolve_accessible_client(
            conn,
            workspace_id,
            user,
            module="hub",
            capability="manage_work",
            require_kind="client",
        )

        evaluation = evaluate_offer_preview(payload)
        value_score = evaluation["value_score"]
        stack = evaluation["offer_stack"]
        verdict = evaluation["board_verdict"]

        row = offer_lab_repo.create_validation(
            conn=conn,
            workspace_id=workspace["workspace_id"],
            tenant_organization_id=workspace["organization_id"],
            user_id=user.id,
            title=payload.title,
            product_or_service=payload.product_or_service,
            target_audience=payload.target_audience,
            current_price_cents=payload.current_price_cents,
            status="reviewed" if verdict.overall_recommendation == "proceed" else "draft",
            value_equation=payload.value_equation.model_dump(),
            value_score=value_score,
            problems_and_solutions=[p.model_dump() for p in payload.problems_and_solutions],
            offer_stack=stack.model_dump(),
            board_verdict=verdict.model_dump(),
        )

        client_hub_repo.write_audit(
            conn,
            user.id,
            workspace["organization_id"],
            "offer_validation.created",
            {
                "workspace_id": str(workspace["workspace_id"]),
                "validation_id": str(row["id"]),
                "title": payload.title,
                "value_score": value_score,
                "verdict": verdict.overall_recommendation,
            },
        )

    return _map_response(row)


def delete_workspace_validation(
    workspace_id: UUID,
    validation_id: UUID,
    user: CurrentUserResponse,
) -> bool:
    with connect() as conn:
        workspace = resolve_accessible_client(
            conn,
            workspace_id,
            user,
            module="hub",
            capability="manage_work",
            require_kind="client",
        )
        deleted = offer_lab_repo.delete_validation(conn, validation_id, workspace["workspace_id"])
        if not deleted:
            raise HTTPException(status_code=404, detail="Validação não encontrada para exclusão.")

        client_hub_repo.write_audit(
            conn,
            user.id,
            workspace["organization_id"],
            "offer_validation.deleted",
            {"workspace_id": str(workspace["workspace_id"]), "validation_id": str(validation_id)},
        )
        return True


def _map_response(row) -> OfferValidationResponse:
    d = dict(row)
    return OfferValidationResponse(
        id=d["id"],
        workspace_id=d["workspace_id"],
        title=d["title"],
        product_or_service=d["product_or_service"],
        target_audience=d["target_audience"],
        current_price_cents=d["current_price_cents"],
        status=d["status"],
        value_equation=ValueEquation(**d["value_equation"]),
        value_score=float(d["value_score"]),
        problems_and_solutions=[ProblemSolutionItem(**p) for p in d.get("problems_and_solutions", [])],
        offer_stack=OfferStack(**d["offer_stack"]),
        board_verdict=BoardVerdict(**d["board_verdict"]),
        created_by=d.get("created_by"),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )
