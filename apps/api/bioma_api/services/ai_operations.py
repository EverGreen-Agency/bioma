from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import ai_operations as repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.schemas.ai_operations import (
    AiCostTotal,
    AiFinOpsDashboard,
    AiQuotaSnapshotCreate,
    AiQuotaSnapshotSummary,
    AiSubscriptionCreate,
    AiSubscriptionSummary,
    AiSubscriptionUpdate,
    AiUsageEventCreate,
    AiUsageSummary,
    WorkflowDefinitionSummary,
    WorkflowRunCreate,
    WorkflowRunSummary,
    WorkflowStepComplete,
    WorkflowStepRunSummary,
    WorkflowTemplateSummary,
)
from bioma_api.schemas.auth import CurrentUserResponse


WORKFLOW_TEMPLATES: dict[str, dict[str, Any]] = {
    "commercial-proposal": {
        "slug": "commercial-proposal",
        "name": "Proposta comercial EG",
        "version": 2,
        "description": "Extrai contexto e dores, constrói a proposta e exige revisão comercial antes do uso.",
        "source_ref": "squads/eg_proposals/squad.yaml",
        "input_schema": {"required": ["opportunity"], "properties": {"opportunity": {"type": "string"}}},
        "steps": [
            {"key": "scout", "name": "Leitura da oportunidade", "description": "Estrutura contexto, dores, entregáveis e stack.", "interactive": False, "task_kind": "content_draft", "capability": "content"},
            {"key": "closer", "name": "Proposta e revisão", "description": "Redige a proposta no padrão EG e aguarda aprovação.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
        ],
    },
    "client-onboarding": {
        "slug": "client-onboarding",
        "name": "Onboarding de cliente no Bioma",
        "version": 3,
        "description": "Converte contrato e contexto em workspace, projetos, acessos, integrações e plano de entrega no Bioma.",
        "source_ref": "squads/eg_setup/squad.yaml",
        "input_schema": {"required": ["client_context"], "properties": {"client_context": {"type": "string"}}},
        "steps": [
            {"key": "scope", "name": "Escopo contratado", "description": "Extrai obrigações, limites e dados da empresa.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "workspace", "name": "Arquitetura operacional", "description": "Planeja projetos, listas, tarefas e views nativas do Bioma.", "interactive": True, "task_kind": "code_agent", "capability": "code"},
            {"key": "integrations", "name": "CRM e integrações", "description": "Define Kommo, SleekFlow ou conectores aplicáveis sem ativação automática.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "accesses", "name": "Inventário de acessos", "description": "Prepara solicitações para o cofre, sem incluir segredos no workflow.", "interactive": True, "task_kind": "content_draft", "capability": "content"},
            {"key": "handoff", "name": "Handoff ao cliente", "description": "Consolida entregas, responsáveis e mensagem de boas-vindas.", "interactive": False, "task_kind": "content_draft", "capability": "content"},
        ],
    },
    "linkedin-content": {
        "slug": "linkedin-content",
        "name": "Conteúdo LinkedIn",
        "version": 2,
        "description": "Pesquisa, estratégia, redação e revisão factual para uma esteira de LinkedIn.",
        "source_ref": "_opensquad/_memory/banco_ideias/docs/pesquisa-academica.md",
        "input_schema": {"required": ["brief"], "properties": {"brief": {"type": "string"}, "brand_context": {"type": "string"}}},
        "steps": [
            {"key": "research", "name": "Pesquisa e evidências", "description": "Reúne fontes e separa fatos de hipóteses.", "interactive": False, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "strategy", "name": "Ângulo editorial", "description": "Define tese, público, formato e objetivo.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "draft", "name": "Redação", "description": "Produz rascunho aderente à voz da marca.", "interactive": False, "task_kind": "content_draft", "capability": "content"},
            {"key": "quality", "name": "Revisão factual e de marca", "description": "Bloqueia publicação até validação humana.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
        ],
    },
    "tech-delivery": {
        "slug": "tech-delivery",
        "name": "Entrega Tech contratual",
        "version": 2,
        "description": "Transforma contrato e documento técnico em backlog, evidências GitHub e atualização compreensível ao cliente.",
        "source_ref": "_opensquad/_memory/engenharia/mod-contratos/spec.md",
        "input_schema": {"required": ["contract_scope"], "properties": {"contract_scope": {"type": "string"}, "technical_document": {"type": "string"}}},
        "steps": [
            {"key": "contract", "name": "Leitura contratual", "description": "Extrai entregáveis, critérios de aceite e restrições.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "technical_scope", "name": "Escopo técnico", "description": "Relaciona contrato, especificação e fases anteriores.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "backlog", "name": "Backlog rastreável", "description": "Gera listas, tarefas, dependências e marcos no Bioma.", "interactive": False, "task_kind": "code_agent", "capability": "code"},
            {"key": "github_evidence", "name": "Evidências GitHub", "description": "Associa issues, PRs e commits por leitura; escrita externa exige HITL próprio.", "interactive": True, "task_kind": "code_agent", "capability": "code"},
            {"key": "client_update", "name": "Atualização ao cliente", "description": "Traduz avanço, bloqueios, testes e próximos passos.", "interactive": True, "task_kind": "content_draft", "capability": "content"},
        ],
    },
    "brand-book": {
        "slug": "brand-book",
        "name": "Brand book operacional",
        "version": 1,
        "description": "Transforma contexto de negócio, público e referências em fundação estratégica e guia de voz revisável.",
        "source_ref": "_opensquad/_memory/company.md",
        "input_schema": {"required": ["brand_context"], "properties": {"brand_context": {"type": "string"}, "references": {"type": "string"}}},
        "steps": [
            {"key": "diagnosis", "name": "Diagnóstico de marca", "description": "Extrai posicionamento, público, oferta, diferenciais, evidências e lacunas sem inventar fatos.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "platform", "name": "Plataforma de marca", "description": "Define essência, promessa, pilares, personalidade e mensagens prioritárias.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "voice", "name": "Voz e linguagem", "description": "Produz princípios de voz, vocabulário, exemplos e restrições editoriais.", "interactive": False, "task_kind": "content_draft", "capability": "content"},
            {"key": "book", "name": "Brand book consolidado", "description": "Consolida o material com rastreabilidade entre fatos, hipóteses e decisões aprovadas.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
        ],
    },
    "video-script": {
        "slug": "video-script",
        "name": "Roteiro de conteúdo em vídeo",
        "version": 1,
        "description": "Cria roteiro orientado a objetivo, canal e voz da marca com revisão humana antes de produção.",
        "source_ref": "_opensquad/_memory/banco_ideias/",
        "input_schema": {"required": ["brief"], "properties": {"brief": {"type": "string"}, "brand_context": {"type": "string"}, "channel": {"type": "string"}}},
        "steps": [
            {"key": "angle", "name": "Ângulo e promessa", "description": "Define público, tensão, promessa, evidências e chamada para ação.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
            {"key": "script", "name": "Roteiro", "description": "Escreve gancho, desenvolvimento, prova, CTA e indicações de cena.", "interactive": False, "task_kind": "content_draft", "capability": "content"},
            {"key": "review", "name": "Revisão editorial", "description": "Verifica clareza, ritmo, aderência à marca e afirmações factuais.", "interactive": True, "task_kind": "brand_strategy", "capability": "strategy"},
        ],
    },
}


def _eg_organization_id(user: CurrentUserResponse) -> UUID:
    require_platform_admin(user)
    for organization in user.organizations:
        if organization.slug == "eg":
            return organization.id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organização EG ausente da sessão.")


def _monthly_equivalent(amount_cents: int, cycle: str, months: int) -> int:
    divisor = 12 if cycle == "annual" else max(months, 1)
    if cycle == "monthly":
        divisor = 1
    return int((Decimal(amount_cents) / Decimal(divisor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _subscription_summary(row: dict[str, Any]) -> AiSubscriptionSummary:
    quota = None
    if row.get("quota_id"):
        total = row.get("total_units")
        used = row.get("used_units")
        remaining = max(total - used, Decimal(0)) if total is not None and used is not None else None
        quota = AiQuotaSnapshotSummary(
            id=row["quota_id"],
            total_units=total,
            used_units=used,
            remaining_units=remaining,
            unit=row["quota_unit"],
            source=row["quota_source"],
            period_start=row.get("period_start"),
            period_end=row.get("period_end"),
            measured_at=row["measured_at"],
            notes=row.get("quota_notes"),
        )
    return AiSubscriptionSummary(
        id=row["id"],
        provider=row["provider"],
        product_name=row["product_name"],
        billing_mode=row["billing_mode"],
        billing_cycle=row["billing_cycle"],
        billing_cycle_months=row["billing_cycle_months"],
        amount_cents=row["amount_cents"],
        monthly_equivalent_cents=_monthly_equivalent(
            row["amount_cents"], row["billing_cycle"], row["billing_cycle_months"]
        ),
        currency=row["currency"],
        seats=row["seats"],
        status=row["status"],
        renews_at=row.get("renews_at"),
        owner_label=row.get("owner_label"),
        notes=row.get("notes"),
        latest_quota=quota,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def get_finops_dashboard(user: CurrentUserResponse) -> AiFinOpsDashboard:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        subscriptions = [_subscription_summary(row) for row in repo.list_subscriptions(conn, organization_id)]
        usage = [AiUsageSummary(**row) for row in repo.usage_current_month(conn, organization_id)]
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"committed": 0, "usage": 0})
    for subscription in subscriptions:
        if subscription.status == "active":
            totals[subscription.currency]["committed"] += subscription.monthly_equivalent_cents
    for item in usage:
        totals[item.currency]["usage"] += item.known_cost_cents
    return AiFinOpsDashboard(
        subscriptions=subscriptions,
        totals_by_currency=[
            AiCostTotal(
                currency=currency,
                committed_monthly_cents=values["committed"],
                measured_usage_cents=values["usage"],
            )
            for currency, values in sorted(totals.items())
        ],
        usage_current_month=usage,
        generated_at=datetime.now(timezone.utc),
    )


def create_subscription(payload: AiSubscriptionCreate, user: CurrentUserResponse) -> AiFinOpsDashboard:
    organization_id = _eg_organization_id(user)
    data = payload.model_dump()
    with connect() as conn:
        row = repo.create_subscription(conn, organization_id, user.id, data)
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.subscription.created",
            {"subscription_id": str(row["id"]), "provider": data["provider"], "product": data["product_name"]},
        )
    return get_finops_dashboard(user)


def update_subscription(
    subscription_id: UUID,
    payload: AiSubscriptionUpdate,
    user: CurrentUserResponse,
) -> AiFinOpsDashboard:
    organization_id = _eg_organization_id(user)
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        if not repo.update_subscription(conn, organization_id, subscription_id, user.id, updates):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assinatura não encontrada.")
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.subscription.updated",
            {"subscription_id": str(subscription_id), "fields": sorted(updates)},
        )
    return get_finops_dashboard(user)


def create_quota_snapshot(
    subscription_id: UUID,
    payload: AiQuotaSnapshotCreate,
    user: CurrentUserResponse,
) -> AiFinOpsDashboard:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        row = repo.create_quota_snapshot(conn, organization_id, subscription_id, user.id, payload.model_dump())
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assinatura não encontrada.")
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.quota.recorded",
            {"subscription_id": str(subscription_id), "quota_snapshot_id": str(row["id"]), "source": payload.source},
        )
    return get_finops_dashboard(user)


def record_usage(payload: AiUsageEventCreate, user: CurrentUserResponse) -> AiFinOpsDashboard:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        repo.create_usage_event(conn, organization_id, user.id, payload.model_dump())
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.usage.recorded",
            {"provider": payload.provider, "source": payload.source, "external_event_id": payload.external_event_id},
        )
    return get_finops_dashboard(user)


def list_templates(user: CurrentUserResponse) -> list[WorkflowTemplateSummary]:
    _eg_organization_id(user)
    return [WorkflowTemplateSummary(**template) for template in WORKFLOW_TEMPLATES.values()]


def list_definitions(user: CurrentUserResponse) -> list[WorkflowDefinitionSummary]:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        rows = repo.list_definitions(conn, organization_id)
    return [WorkflowDefinitionSummary(**row) for row in rows]


def install_template(slug: str, user: CurrentUserResponse) -> list[WorkflowDefinitionSummary]:
    organization_id = _eg_organization_id(user)
    template = WORKFLOW_TEMPLATES.get(slug)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template de workflow não encontrado.")
    with connect() as conn:
        row = repo.install_definition(conn, organization_id, user.id, template)
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.workflow.installed",
            {"definition_id": str(row["id"]), "slug": slug, "version": template["version"]},
        )
    return list_definitions(user)


def _run_summary(row: dict[str, Any], steps: list[dict[str, Any]]) -> WorkflowRunSummary:
    return WorkflowRunSummary(
        **row,
        steps=[WorkflowStepRunSummary(**step) for step in steps],
    )


def list_runs(user: CurrentUserResponse) -> list[WorkflowRunSummary]:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        rows = repo.list_runs(conn, organization_id)
        steps = repo.list_run_steps(conn, [row["id"] for row in rows])
    by_run: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    for step in steps:
        by_run[step["run_id"]].append(step)
    return [_run_summary(row, by_run[row["id"]]) for row in rows]


def create_run(payload: WorkflowRunCreate, user: CurrentUserResponse) -> WorkflowRunSummary:
    organization_id = _eg_organization_id(user)
    data = payload.model_dump()
    with connect() as conn:
        definition = repo.get_definition(conn, organization_id, payload.definition_id)
        if not definition or definition["status"] != "active":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow ativo não encontrado.")
        required_fields = definition["input_schema"].get("required", [])
        missing_fields = [field for field in required_fields if not data["input"].get(field)]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Campos obrigatórios ausentes no workflow: {', '.join(missing_fields)}.",
            )
        if payload.workspace_id and not repo.workspace_exists(conn, payload.workspace_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
        row = repo.create_run(conn, organization_id, user.id, definition, data)
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.workflow.requested",
            {"run_id": str(row["id"]), "definition_id": str(payload.definition_id), "idempotency_key": payload.idempotency_key},
        )
    return next(run for run in list_runs(user) if run.id == row["id"])


def approve_run(run_id: UUID, user: CurrentUserResponse) -> WorkflowRunSummary:
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        row = repo.approve_run(conn, organization_id, run_id, user.id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Execução inexistente ou fora do estado de aprovação.",
            )
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.workflow.approved", {"run_id": str(run_id)},
        )
    return next(run for run in list_runs(user) if run.id == run_id)


def complete_step(
    run_id: UUID,
    step_key: str,
    payload: WorkflowStepComplete,
    user: CurrentUserResponse,
) -> WorkflowRunSummary:
    organization_id = _eg_organization_id(user)
    data = payload.model_dump()
    with connect() as conn:
        current_run = repo.get_run(conn, organization_id, run_id)
        if not current_run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada.")
        if payload.cost_cents is not None and payload.currency.upper() != current_run["currency"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A moeda do custo da etapa deve ser a mesma moeda da execução.",
            )
        step = repo.complete_step(conn, organization_id, run_id, step_key, data)
        if not step:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Etapa inexistente, fora de ordem ou execução ainda não aprovada.",
            )
        if payload.provider:
            run = repo.get_run(conn, organization_id, run_id)
            repo.create_usage_event(
                conn,
                organization_id,
                user.id,
                {
                    "workspace_id": run["workspace_id"],
                    "workflow_run_id": run_id,
                    "provider": payload.provider,
                    "model": payload.model,
                    "source": f"workflow:{run['definition_slug']}:{step_key}",
                    "external_event_id": payload.external_event_id,
                    "input_units": payload.input_units,
                    "output_units": payload.output_units,
                    "cached_units": payload.cached_units,
                    "cost_cents": payload.cost_cents,
                    "currency": payload.currency,
                    "metadata": {"step_key": step_key},
                },
            )
        client_hub_repo.write_audit(
            conn, user.id, organization_id, "ai.workflow.step_completed",
            {"run_id": str(run_id), "step_key": step_key, "cost_cents": payload.cost_cents},
        )
    return next(run for run in list_runs(user) if run.id == run_id)
