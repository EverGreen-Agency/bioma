from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

CopilotSurface = Literal["task", "workspace"]
ActionStatus = Literal["executed", "proposed", "pending_confirmation", "failed"]


class CopilotAttachment(BaseModel):
    """Arquivo anexado a uma mensagem.

    `has_text` é o que decide se o copiloto consegue de fato usar o conteúdo:
    documento vira texto e roda em qualquer provedor; imagem precisa de modelo
    com visão; áudio precisa de transcrição.
    """
    id: UUID
    thread_id: UUID | None
    file_name: str
    content_type: str
    size_bytes: int
    kind: Literal["image", "audio", "document"]
    extraction_status: Literal["pending", "extracted", "unsupported", "failed", "not_needed"]
    extraction_error: str | None
    truncated_chars: int | None
    has_text: bool
    created_at: datetime


class CopilotRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    surface: CopilotSurface = "workspace"
    task_id: UUID | None = None
    workspace_id: UUID | None = None
    project_id: UUID | None = None
    opportunity_id: UUID | None = None
    proposal_id: UUID | None = None
    expert: str | None = Field(default=None, max_length=80)
    # Continua uma conversa existente. Ausente = abre uma nova.
    thread_id: UUID | None = None
    # Anexos enviados antes desta mensagem, adotados pela thread no envio.
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=10)
    # Busca na web é permitida por decisão do Eduardo, mas sempre com fonte.
    allow_web_search: bool = True
    # dry_run devolve o plano sem executar nada — usado na pré-visualização.
    dry_run: bool = False


class CopilotAction(BaseModel):
    name: str
    label: str
    params: dict[str, Any] = Field(default_factory=dict)
    why: str = ""
    status: ActionStatus
    detail: str | None = None
    # Como desfazer o que foi executado. Ação reversível sem dica de desfazer é
    # bug de implementação, não desenho.
    undo_hint: str | None = None


class CopilotSource(BaseModel):
    """`bioma` = origem interna (tela/tabela); `web` = URL realmente visitada."""
    kind: Literal["bioma", "web"]
    reference: str


class CopilotBlock(BaseModel):
    """Bloco renderizável do catálogo do Bioma — nunca HTML/JS arbitrário."""
    id: str = Field(min_length=1, max_length=120)
    kind: Literal[
        "markdown", "entity_summary", "action_list", "source_list",
        "task_list", "timeline", "approval", "form", "metric", "artifact",
    ]
    title: str | None = Field(default=None, max_length=240)
    data: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)


class CopilotResponse(BaseModel):
    thread_id: UUID
    # Chave da trilha desta resposta: com ela a interface abre a auditoria do
    # que aconteceu sem precisar caçar por data e hora.
    run_id: UUID
    answer: str
    generation_mode: Literal["live", "preview"]
    confidence: Literal["alta", "media", "baixa"]
    actions: list[CopilotAction] = Field(default_factory=list)
    sources: list[CopilotSource] = Field(default_factory=list)
    blocks: list[CopilotBlock] = Field(default_factory=list)


class CopilotThreadSummary(BaseModel):
    id: UUID
    title: str | None
    surface: CopilotSurface
    workspace_id: UUID | None
    task_id: UUID | None
    status: Literal["active", "archived"]
    run_count: int
    last_message: str | None
    last_message_at: datetime
    created_at: datetime


class CopilotRunStep(BaseModel):
    position: int
    kind: Literal["dossier", "plan", "action", "persist"]
    label: str
    status: Literal["ok", "skipped", "blocked", "failed"]
    detail: str | None
    payload: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None


class CopilotQuotaBucket(BaseModel):
    """Um limite da conta — Codex e Claude reportam mais de um (janela curta e
    longa, por família de modelo). `source`/`confidence` vêm de quem mediu:
    `provider_api` + `authoritative` é o próprio provedor dizendo; qualquer
    outra coisa é estimativa e a tela precisa deixar isso visível."""
    bucket_key: str
    scope: str
    model_id: str | None
    remaining_percent: Decimal | None
    unit: str
    resets_at: datetime | None
    source: str
    confidence: str
    measured_at: datetime


class CopilotRoutedAccountQuota(BaseModel):
    account_id: UUID
    display_name: str
    channel: str
    # Vazio = conta existe mas ainda não tem coleta de cota rodada. Não é erro,
    # é "ainda não medimos" — diferente de "não sobrou nada".
    buckets: list[CopilotQuotaBucket] = Field(default_factory=list)


class CopilotRunTrace(BaseModel):
    """O que aconteceu numa execução. Não é o que o copiloto disse que fez."""
    id: UUID
    thread_id: UUID
    message: str
    answer: str | None
    status: Literal["running", "completed", "failed"]
    error_message: str | None
    # `preview` = prévia local, nenhum token gasto e nenhum modelo consultado.
    generation_mode: Literal["live", "preview"] | None
    provider: str | None
    model: str | None
    confidence: str | None
    dossier_summary: dict[str, Any] = Field(default_factory=dict)
    memories_used: list[dict[str, Any]] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    response_blocks: list[CopilotBlock] = Field(default_factory=list)
    # Índice do que estava anexado NAQUELE turno. Anexar depois não pode
    # reescrever a história de uma resposta dada sem o arquivo.
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    input_tokens: int | None
    output_tokens: int | None
    # Nulo = sem custo em dinheiro conhecido — ou o modelo não está em
    # `model_pricing.py`, ou (quando `routed_account` abaixo está preenchido) a
    # execução rodou na cota da assinatura, que não é cobrada por token.
    cost_cents: int | None
    duration_ms: int | None
    created_at: datetime
    steps: list[CopilotRunStep] = Field(default_factory=list)
    # Preenchido quando a execução rodou por uma conta do plano de roteamento
    # (Codex CLI, Claude Code CLI) em vez da chave de API.
    routed_account: CopilotRoutedAccountQuota | None = None


class CopilotDailyUsage(BaseModel):
    """Um ponto da série diária — o que alimenta os gráficos de tendência."""
    day: date
    runs: int
    routed_runs: int
    failed_runs: int
    cost_cents: int
    input_tokens: int
    output_tokens: int


class CopilotProviderUsage(BaseModel):
    """Quebra por provedor+modelo na janela — de onde as respostas vieram."""
    provider: str
    model: str
    runs: int
    routed_runs: int
    cost_cents: int


class CopilotUsageSummary(BaseModel):
    runs: int
    failed_runs: int
    preview_runs: int
    # Execuções por CHAVE DE API cujo modelo não está na tabela de preços — gap
    # de verdade. Execução roteada por assinatura sem custo em dinheiro NÃO
    # entra aqui (ver `routed_runs`): não ter preço por token é o esperado.
    runs_without_cost: int
    # Quantas execuções rodaram na cota da assinatura em vez da chave de API.
    routed_runs: int
    input_tokens: int
    output_tokens: int
    cost_cents: int
    avg_duration_ms: int
    # Contas de assinatura que atenderam nesta janela, com a cota ATUAL de
    # cada uma (não uma foto de quando a execução rodou — cota é estado
    # presente, e o que importa é "quanto sobra agora").
    routed_accounts: list[CopilotRoutedAccountQuota] = Field(default_factory=list)
    # Série diária e quebra por provedor/modelo — o que alimenta os gráficos.
    # Sem preenchimento de dias vazios: dia sem execução simplesmente não
    # aparece, como as demais séries diárias do Bioma.
    daily: list[CopilotDailyUsage] = Field(default_factory=list)
    by_provider: list[CopilotProviderUsage] = Field(default_factory=list)


class CopilotCommand(BaseModel):
    """Item do menu de `/` na interface."""
    name: str
    label: str
    description: str
    requires_confirmation: bool


PlanStatus = Literal[
    "pending_approval", "approved", "running", "completed", "failed", "rejected", "cancelled"
]
PlanStepStatus = Literal["pending", "running", "executed", "failed", "skipped", "blocked"]


class CopilotPlanRequest(BaseModel):
    """Objetivo em linguagem natural — o copiloto monta a sequência."""
    goal: str = Field(min_length=2, max_length=2000)
    workspace_id: UUID | None = None


class CopilotPlanStep(BaseModel):
    id: UUID
    position: int
    action_name: str
    label: str
    params: dict[str, Any] = Field(default_factory=dict)
    why: str = ""
    status: PlanStepStatus
    detail: str | None = None
    undo_hint: str | None = None


class CopilotPlan(BaseModel):
    id: UUID
    workspace_id: UUID | None
    goal: str
    summary: str
    status: PlanStatus
    generation_mode: Literal["live", "preview"]
    # Etapas que continuam pedindo confirmação individual mesmo com o plano
    # aprovado (ação visível ao cliente).
    requires_confirmation_count: int
    error_message: str | None = None
    steps: list[CopilotPlanStep] = Field(default_factory=list)
    # Perguntas que o plano não conseguiu responder sozinho — substituem o
    # formulário que o usuário teria que preencher antes.
    open_questions: list[str] = Field(default_factory=list)
