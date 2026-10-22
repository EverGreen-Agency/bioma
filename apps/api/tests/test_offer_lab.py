import pytest
from bioma_api.schemas.offer_lab import (
    OfferEvaluatePayload,
    ProblemSolutionItem,
    ValueEquation,
)
from bioma_api.services.offer_lab import (
    calculate_value_score,
    evaluate_offer_preview,
    generate_board_verdict,
)


def test_calculate_value_score_grand_slam():
    """Valida a fórmula da Equação de Valor para uma Grand Slam Offer."""
    ve = ValueEquation(
        dream_outcome=9.0,
        perceived_likelihood=8.0,
        time_delay=2.0,
        effort_and_sacrifice=2.0,
    )
    score = calculate_value_score(ve)
    # (9 * 8) / (2 * 2) = 72 / 4 = 18.0
    assert score == 18.0


def test_calculate_value_score_commodity():
    """Valida a fórmula para uma oferta comoditizada com alto atrito e demora."""
    ve = ValueEquation(
        dream_outcome=5.0,
        perceived_likelihood=4.0,
        time_delay=8.0,
        effort_and_sacrifice=9.0,
    )
    score = calculate_value_score(ve)
    # (5 * 4) / (8 * 9) = 20 / 72 = 0.28
    assert score == 0.28


def test_board_verdict_detects_dealbreakers():
    """Valida que o conselho virtual sinaliza dealbreakers de esforço e demora."""
    ve = ValueEquation(
        dream_outcome=8.0,
        perceived_likelihood=3.0,  # Baixa certeza
        time_delay=8.0,            # Demora excessiva
        effort_and_sacrifice=8.0,  # Esforço excessivo
    )
    verdict = generate_board_verdict(
        product="Consultoria Genérica",
        audience="PMEs",
        price_cents=500_000,
        ve=ve,
        problems=[],
        stack=None,
    )

    assert len(verdict.dealbreakers) >= 2
    assert verdict.overall_recommendation in ("refine_offer", "abort")
    assert any("Esforço e atrito" in d for d in verdict.dealbreakers)
    assert any("Time-to-Value" in d for d in verdict.dealbreakers)


def test_evaluate_offer_preview_generates_stack():
    payload = OfferEvaluatePayload(
        title="Consultoria de Vendas B2B",
        product_or_service="Implementação de CRM e Prospecção Ativa",
        target_audience="Indústrias e Distribuidores",
        current_price_cents=1_500_000,
        value_equation=ValueEquation(
            dream_outcome=8.5,
            perceived_likelihood=8.0,
            time_delay=2.5,
            effort_and_sacrifice=2.0,
        ),
        problems_and_solutions=[
            ProblemSolutionItem(
                obstacle="Falta de tempo da equipe para configurar o CRM",
                timing="before_buying",
                solution="Onboarding Done-For-You entregue em 5 dias úteis",
                delivery_vehicle="done_for_you",
                cost_to_deliver="low",
                perceived_value="high",
            )
        ],
    )
    result = evaluate_offer_preview(payload)

    assert "value_score" in result
    assert result["value_score"] > 10.0
    assert result["offer_stack"].guarantee.type == "conditional"
    assert result["board_verdict"].overall_recommendation == "proceed"
