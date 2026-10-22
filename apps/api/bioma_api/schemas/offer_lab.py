from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ValueEquation(BaseModel):
    dream_outcome: float = Field(ge=0.0, le=10.0, description="Magnitude do resultado prometido (0 a 10)")
    perceived_likelihood: float = Field(ge=0.0, le=10.0, description="Certeza percebida de atingimento (0 a 10)")
    time_delay: float = Field(ge=1.0, le=10.0, description="Tempo até o primeiro resultado (1 instantâneo a 10 demorado)")
    effort_and_sacrifice: float = Field(ge=1.0, le=10.0, description="Esforço e atrito exigidos do cliente (1 mínimo a 10 extenuante)")
    notes: dict[str, str] = Field(default_factory=dict, description="Justificativas e notas de cada pilar")


class ProblemSolutionItem(BaseModel):
    obstacle: str = Field(description="Obstáculo ou atrito na visão do cliente")
    timing: str = Field(default="before_buying", description="before_buying | during_delivery | after_purchase")
    solution: str = Field(description="Como o produto/bônus elimina este atrito")
    delivery_vehicle: str = Field(default="done_for_you", description="done_for_you | software | 1_on_1 | group | checklist")
    cost_to_deliver: str = Field(default="low", description="low | medium | high")
    perceived_value: str = Field(default="high", description="low | medium | high | extreme")


class OfferBonus(BaseModel):
    title: str = Field(description="Título atraente do bônus")
    description: str = Field(description="O que entrega e qual atrito resolve")
    perceived_value_cents: int = Field(default=0, ge=0, description="Valor nominal percebido em centavos")
    delivery_cost: str = Field(default="low", description="Custo real de entrega")


class RiskReversalGuarantee(BaseModel):
    type: str = Field(default="conditional", description="unconditional | conditional | anti_guarantee | performance_based")
    title: str = Field(default="Garantia de Resultado Condicionado")
    terms: str = Field(description="Termos claros da garantia sem ambiguidade")
    conditions: list[str] = Field(default_factory=list, description="Condições que o cliente precisa cumprir")


class OfferStack(BaseModel):
    core_offer_name: str
    core_offer_description: str
    magic_name: str = Field(default="", description="Fórmula M.A.G.I.C: Magnet + Avatar + Goal + Interval + Container")
    bonuses: list[OfferBonus] = Field(default_factory=list)
    guarantee: RiskReversalGuarantee
    scarcity_urgency: str = Field(default="", description="Gatilho de urgência ou escassez real e auditável")


class BoardVerdict(BaseModel):
    hormozi_offers_score: float = Field(ge=0.0, le=10.0)
    hormozi_verdict: str
    thiel_monopoly_score: float = Field(ge=0.0, le=10.0)
    thiel_verdict: str
    jobs_product_score: float = Field(ge=0.0, le=10.0)
    jobs_verdict: str
    dealbreakers: list[str] = Field(default_factory=list)
    overall_recommendation: str = Field(default="proceed", description="proceed | refine_offer | abort")


class OfferEvaluatePayload(BaseModel):
    title: str
    product_or_service: str
    target_audience: str
    current_price_cents: int = Field(ge=0, default=0)
    value_equation: ValueEquation
    problems_and_solutions: list[ProblemSolutionItem] = Field(default_factory=list)
    offer_stack: OfferStack | None = None


class OfferValidationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    product_or_service: str
    target_audience: str
    current_price_cents: int
    status: str
    value_equation: ValueEquation
    value_score: float
    problems_and_solutions: list[ProblemSolutionItem] = Field(default_factory=list)
    offer_stack: OfferStack
    board_verdict: BoardVerdict
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
