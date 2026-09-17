"""Copiloto do Bioma — interpreta, propõe e executa o que for reversível.

Contrato de segurança (decisões do Eduardo em 2026-07-30):
- ação **reversível** executa direto e o retorno diz como desfazer;
- ação **visível ao cliente** nunca executa aqui: volta como `pending_confirmation`;
- toda resposta carrega fontes; dado do Bioma cita a origem, web cita a URL;
- **só EG**: `require_platform_admin` em toda entrada.

O plano vem do modelo, mas a autoridade é daqui: nome fora do catálogo, parâmetro
inválido ou ação irreversível são recusados independentemente do que o texto diga.
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_platform_admin
from bioma_api.db import connect
from bioma_api.feature_flags import FEATURE_CATALOG
from bioma_api.model_pricing import cost_cents
from bioma_api.repositories import agent_memory as memory_repo
from bioma_api.repositories import ai_routing as ai_routing_repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import copilot_attachments as attachments_repo
from bioma_api.repositories import copilot_traces as trace_repo
from bioma_api.repositories import improvement_requests as improvement_repo
from bioma_api.repositories import knowledge as knowledge_repo
from bioma_api.repositories import proposals as proposals_repo
from bioma_api.repositories import tasks as tasks_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.services import copilot_attachments as attachments_service
from bioma_api.services.ai_operations import _eg_organization_id
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.copilot import (
    CopilotAction,
    CopilotBlock,
    CopilotRequest,
    CopilotResponse,
    CopilotSource,
)
from bioma_api.worker_bridge import (
    copilot_action_catalog,
    copilot_plan_routed_safe,
    copilot_plan_safe,
    rank_copilot_candidates,
)

# Por superfície, o que o copiloto pode propor. Uma superfície não enxerga ação
# que não faz sentido nela — reduz o espaço de erro do modelo.
SURFACE_ACTIONS = {
    "task": [
        "create_subtasks", "set_due_date", "set_status", "add_comment",
        "summarize_thread", "answer_only", "remember_fact", "propose_skill",
        "request_improvement",
    ],
    "workspace": [
        "answer_only", "summarize_thread", "remember_fact", "propose_skill",
        "request_improvement", "capture_opportunity",
    ],
}

HARNESS_TOOL_ACTIONS = {
    "update_task_status": {"set_status"},
}


def _enabled_harness_tools(user: CurrentUserResponse) -> set[str] | None:
    """`None` preserva o contrato anterior até existir configuração explícita."""
    organization_id = _eg_organization_id(user)
    with connect() as conn:
        harness = ai_routing_repo.get_harness_config(conn, organization_id)
    return set(harness.get("enabled_tools") or []) if harness else None


def _allowed_actions(surface: str, enabled_tools: set[str] | None) -> list[str]:
    allowed = list(SURFACE_ACTIONS.get(surface, ["answer_only"]))
    if enabled_tools is None:
        return allowed
    controlled_actions = set().union(*HARNESS_TOOL_ACTIONS.values())
    enabled_actions = set().union(
        *(actions for tool, actions in HARNESS_TOOL_ACTIONS.items() if tool in enabled_tools)
    )
    return [name for name in allowed if name not in controlled_actions or name in enabled_actions]


def run(payload: CopilotRequest, user: CurrentUserResponse) -> CopilotResponse:
    require_platform_admin(user)

    catalog = copilot_action_catalog()
    enabled_tools = _enabled_harness_tools(user)
    allowed = _allowed_actions(payload.surface, enabled_tools)

    # O dossiê vem antes de abrir a execução porque é ele que valida as
    # referências: tarefa ou workspace inexistente tem que virar 404 limpo, não
    # uma thread órfã apontando para um id que não existe.
    started = time.monotonic()
    dossier, context, task_row = _build_dossier(payload, user, enabled_tools)

    # Anexos entram no dossiê como conteúdo, e na trilha como índice. Documento
    # vira texto e roda em qualquer provedor — inclusive na CLI, na cota da
    # assinatura. Imagem e áudio entram com o motivo de não terem sido lidos,
    # porque o modelo precisa saber o que NÃO tem: sem isso ele responde sobre
    # o arquivo como se tivesse lido.
    attachments_for_trace: list[dict] = []
    if payload.attachment_ids:
        with connect() as conn:
            for_prompt, attachments_for_trace = attachments_service.load_for_prompt(
                conn, payload.attachment_ids, user.id
            )
        if for_prompt:
            dossier["attachments"] = for_prompt

    dossier_ms = _elapsed_ms(started)

    # A conversa é contínua: sem thread, cada pergunta começaria do zero e o
    # copiloto nunca acompanharia um assunto ao longo do dia.
    thread, run_row = _open_run(payload, user)
    steps = _StepRecorder(run_row["id"])
    steps.record("dossier", "Montar dossiê do escopo", "ok", None, {}, dossier_ms)
    steps.annotate(_dossier_summary(dossier))

    try:
        plan_request = {
            "message": payload.message,
            "surface": payload.surface,
            "context": context,
            "dossier": dossier,
            "allowed_actions": allowed,
            "allow_web_search": payload.allow_web_search,
            "history": _thread_history(thread["id"]),
        }
        try:
            result = _plan_with_routing(plan_request, payload.surface, steps)
        except Exception as exc:
            steps.fail("plan", "Pedir plano ao modelo", str(exc)[:500])
            _close_run(run_row["id"], {"status": "failed", "error_message": str(exc)[:2000],
                                       "duration_ms": _elapsed_ms(started)})
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="O copiloto não conseguiu responder agora. Tente novamente.",
            ) from exc

        output = result["output"]
        actions: list[CopilotAction] = []

        for proposed in output.get("actions", []):
            name = proposed.get("name")
            spec = catalog.get(name)
            if not spec or name not in allowed:
                # Nome inventado ou fora da superfície: descartado sem executar.
                # Registrado assim mesmo — descarte silencioso esconde tentativa
                # do modelo de sair do catálogo, que é exatamente o que auditoria
                # precisa enxergar.
                steps.record(
                    "action", f"Descartada: {name or '(sem nome)'}", "skipped",
                    "Fora do catálogo ou da superfície — não executada.",
                    {"proposed_name": name, "surface": payload.surface},
                )
                continue
            try:
                params = json.loads(proposed.get("params") or "{}")
            except json.JSONDecodeError:
                params = {}
            if not isinstance(params, dict):
                params = {}

            if not spec["reversible"]:
                action = CopilotAction(
                    name=name,
                    label=spec["label"],
                    params=params,
                    why=proposed.get("why", ""),
                    status="pending_confirmation",
                    detail="Ação visível ao cliente — precisa da sua confirmação.",
                )
                steps.record("action", spec["label"], "blocked", action.detail, {"params": params})
                actions.append(action)
                continue

            if payload.dry_run:
                action = CopilotAction(
                    name=name,
                    label=spec["label"],
                    params=params,
                    why=proposed.get("why", ""),
                    status="proposed",
                    detail="Pré-visualização: nada foi alterado.",
                )
                steps.record("action", spec["label"], "skipped", action.detail, {"params": params})
                actions.append(action)
                continue

            action_started = time.monotonic()
            action = _execute(name, spec, params, proposed.get("why", ""), task_row, user, payload.workspace_id)
            if action.status == "executed" and name == "capture_opportunity" and params.get("opportunity_id"):
                with connect() as conn:
                    trace_repo.bind_thread_entities(
                        conn,
                        thread["id"],
                        user.id,
                        [("opportunity", params["opportunity_id"])],
                    )
            steps.record(
                "action", spec["label"],
                "ok" if action.status == "executed" else "failed",
                action.detail,
                {"params": params, "undo_hint": action.undo_hint},
                _elapsed_ms(action_started),
            )
            actions.append(action)

        skill_ids_by_name: dict[str, str] = context.get("skill_ids_by_name") or {}
        used_skill_names = [name for name in output.get("skills_used", []) if name in skill_ids_by_name]
        if used_skill_names:
            with connect() as conn:
                for name in used_skill_names:
                    memory_repo.record_skill_use(conn, skill_ids_by_name[name])

        sources = [
            CopilotSource(kind=source.get("kind", "bioma"), reference=source.get("reference", ""))
            for source in output.get("sources", [])
            if source.get("reference")
        ]
        blocks = _response_blocks(output.get("answer", ""), actions, sources, context)

        usage = result.get("usage") or {}
        model = result.get("model")
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        # Custo reportado pela própria conta (a CLI do Claude devolve o valor da
        # execução) vale mais que a nossa tabela de preços — é o número que ele
        # cobrou, não o que calculamos.
        reported_cost = result.get("cost_cents")
        routed_account = result.get("routed_account")

        if routed_account is not None:
            # Rodou na cota da assinatura — nunca aplicar `model_pricing.py`
            # aqui. Aquela tabela é preço por token da API paga; o `model_id`
            # de uma conta de assinatura pode coincidir por acaso com um nome
            # de modelo precificado ali, e isso produziria um custo em dólar
            # FALSO para uma execução que não é cobrada por token — o inverso
            # exato do que a trilha existe para evitar. Só o que a própria CLI
            # reportou (Claude Code) é dinheiro real; o resto fica em branco,
            # e quem quer saber "quanto gastei" olha a cota, não um valor
            # inventado.
            final_cost = reported_cost
        else:
            final_cost = (
                reported_cost if reported_cost is not None else cost_cents(model, input_tokens, output_tokens)
            )

        _close_run(
            run_row["id"],
            {
                "status": "completed",
                "answer": output.get("answer", ""),
                "confidence": output.get("confidence", "baixa"),
                "generation_mode": result["generation_mode"],
                "provider": result.get("provider"),
                "model": model,
                "dossier_summary": steps.dossier_summary,
                "memories_used": [
                    {"scope": row["scope"], "title": row["title"]} for row in dossier.get("memories", [])
                ],
                "skills_used": used_skill_names,
                "sources": [source.model_dump() for source in sources],
                "actions": [action.model_dump() for action in actions],
                "response_blocks": [block.model_dump() for block in blocks],
                "attachments": attachments_for_trace,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_cents": final_cost,
                "duration_ms": _elapsed_ms(started),
                "routed_account_id": routed_account.get("account_id") if routed_account else None,
            },
        )

        return CopilotResponse(
            thread_id=thread["id"],
            run_id=run_row["id"],
            answer=output.get("answer", ""),
            generation_mode=result["generation_mode"],
            confidence=output.get("confidence", "baixa"),
            actions=actions,
            sources=sources,
            blocks=blocks,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Falha fora do plano (dossiê, execução, persistência) também precisa
        # fechar a execução — run eternamente "running" na trilha é ruído.
        _close_run(
            run_row["id"],
            {"status": "failed", "error_message": str(exc)[:2000], "duration_ms": _elapsed_ms(started)},
        )
        raise


def _plan_with_routing(plan_request: dict, surface: str, steps: "_StepRecorder") -> dict:
    """Pede o plano usando a COTA DA ASSINATURA antes de gastar chave de API.

    Ordem, e o porquê de cada passo:

    1. Contas do plano de roteamento (`ai_provider_accounts`) — Codex CLI, Claude
       Code CLI, Antigravity. São as assinaturas que o Eduardo já paga; usar a
       chave de API avulsa quando existe cota contratada parada é gastar duas
       vezes pela mesma coisa. A ordem entre elas vem de `rank_candidates`, que
       considera a cota restante e a política ativa.
    2. Se nenhuma conta responder, a chave de API (`OPENAI_API_KEY`).
    3. Se não houver chave, prévia local rotulada (o próprio `copilot_plan_safe`).

    Cada tentativa que falha vira uma etapa `skipped` na trilha, com o motivo.
    Sem isso, "o copiloto usou a API" e "o copiloto tentou a CLI, ela quebrou, e
    caiu para a API" ficam indistinguíveis — e a segunda é a que explica por que
    a fatura subiu.
    """
    candidates = _routing_candidates()
    for candidate in candidates:
        label = f"{candidate['account_name']} ({candidate['channel']})"
        attempt_started = time.monotonic()
        try:
            result = copilot_plan_routed_safe(plan_request, candidate)
            steps.record(
                "plan", f"Plano via {label}", "ok",
                f"Cota da assinatura — modelo {candidate['model_id']}.",
                {"account_id": str(candidate["account_id"]), "channel": candidate["channel"]},
                _elapsed_ms(attempt_started),
            )
            return result
        except Exception as exc:
            steps.record(
                "plan", f"Plano via {label}", "skipped", str(exc)[:400],
                {"channel": candidate["channel"]}, _elapsed_ms(attempt_started),
            )

    attempt_started = time.monotonic()
    result = copilot_plan_safe(plan_request)
    steps.record(
        "plan", f"Plano pela chave de API ({surface})",
        "ok",
        "Nenhuma conta de assinatura disponível." if candidates else None,
        {}, _elapsed_ms(attempt_started),
    )
    return result


def _routing_candidates() -> list[dict]:
    """Contas de assinatura da EG, ordenadas por cota e política.

    Falha de leitura não pode derrubar o copiloto: sem plano de roteamento
    configurado, a lista vazia leva direto para a chave de API, que é o
    comportamento de antes.
    """
    try:
        with connect() as conn:
            organization_id = workspaces_repo.find_eg_tenant_id(conn)
            if not organization_id:
                return []
            rows = ai_routing_repo.list_copilot_candidates(conn, organization_id)
        ranked = rank_copilot_candidates([dict(row) for row in rows])
        return _eligible_routing_candidates(ranked)
    except Exception:
        return []


def _eligible_routing_candidates(ranked: list[dict]) -> list[dict]:
    eligible = [candidate for candidate in ranked if candidate.get("eligible")]
    if eligible and not eligible[0].get("allow_fallback", True):
        return eligible[:1]
    return eligible


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _open_run(payload: CopilotRequest, user: CurrentUserResponse) -> tuple[dict, dict]:
    with connect() as conn:
        thread = trace_repo.get_thread(conn, payload.thread_id) if payload.thread_id else None
        if thread and thread["user_id"] != user.id:
            # Escrever na conversa de outra pessoa não é continuar um assunto.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
        if not thread:
            thread = trace_repo.create_thread(
                conn, user.id, payload.surface, payload.workspace_id, payload.task_id, payload.message
            )
        trace_repo.touch_thread(conn, thread["id"], payload.message)
        # O anexo é enviado enquanto a pessoa ainda escreve, antes de a thread
        # existir. Nasce solto e é adotado aqui.
        attachments_repo.bind_to_thread(conn, payload.attachment_ids, thread["id"])
        entities = [
            (kind, entity_id)
            for kind, entity_id in (
                ("workspace", payload.workspace_id),
                ("project", payload.project_id),
                ("opportunity", payload.opportunity_id),
                ("proposal", payload.proposal_id),
                ("task", payload.task_id),
            )
            if entity_id is not None
        ]
        trace_repo.bind_thread_entities(conn, thread["id"], user.id, entities)
        run_row = trace_repo.start_run(
            conn,
            {
                "thread_id": thread["id"],
                "user_id": user.id,
                "surface": payload.surface,
                "workspace_id": payload.workspace_id,
                "task_id": payload.task_id,
                "message": payload.message,
            },
        )
    return thread, run_row


def _close_run(run_id, data: dict) -> None:
    with connect() as conn:
        trace_repo.finish_run(conn, run_id, data)


def _thread_history(thread_id, limit: int = 8) -> list[dict]:
    """Turnos anteriores da conversa, para o modelo não repetir o que já disse.

    Só pergunta e resposta — o dossiê é remontado a cada turno com dado fresco,
    então reenviar o dossiê antigo só gastaria token com informação vencida.
    """
    with connect() as conn:
        runs = trace_repo.list_runs(conn, thread_id)
    return [
        {"message": row["message"], "answer": row["answer"]}
        for row in runs[-limit:]
        if row.get("answer")
    ]


def _dossier_summary(dossier: dict) -> dict:
    """Índice do que foi lido — não o conteúdo.

    Guardar o dossiê inteiro faria da trilha uma segunda cópia do banco (e uma
    cópia com dado de cliente, sem as regras de acesso do original). O que a
    auditoria precisa é da procedência: quantas tarefas, quais memórias, quais
    habilidades entraram na decisão.
    """
    return {
        "task_in_context": bool(dossier.get("task")),
        "task_comments": len(dossier.get("task_comments") or []),
        "my_tasks": len(dossier.get("my_tasks") or []),
        "memories": len(dossier.get("memories") or []),
        "approved_skills": len(dossier.get("approved_skills") or []),
        "bioma_features": len(dossier.get("bioma_features") or []),
        "knowledge_docs": len(dossier.get("knowledge_index") or []),
        "attachments": len(dossier.get("attachments") or []),
        "portfolio_snapshot": dossier.get("portfolio") or {},
    }


class _StepRecorder:
    """Grava as etapas da execução com o tempo de cada uma.

    Escreve fora da transação da ação: uma etapa que falha ainda precisa aparecer
    na trilha, e um erro ao gravar a trilha nunca pode derrubar a resposta ao
    usuário — auditoria que quebra o produto vira auditoria desligada.
    """

    def __init__(self, run_id) -> None:
        self.run_id = run_id
        self.position = 0
        self.dossier_summary: dict = {}

    def record(self, kind: str, label: str, status_val: str, detail: str | None = None,
               payload: dict | None = None, duration_ms: int | None = None) -> None:
        self.position += 1
        try:
            with connect() as conn:
                trace_repo.add_step(
                    conn, self.run_id, self.position,
                    {"kind": kind, "label": label, "status": status_val, "detail": detail,
                     "payload": payload or {}, "duration_ms": duration_ms},
                )
        except Exception:
            pass

    def fail(self, kind: str, label: str, detail: str) -> None:
        self.record(kind, label, "failed", detail)

    def annotate(self, summary: dict) -> None:
        self.dossier_summary = summary

    def timed(self, kind: str, label: str):
        recorder = self

        class _Timer:
            def __enter__(self):
                self.started = time.monotonic()
                return self

            def __exit__(self, exc_type, exc, tb):
                if exc_type is None:
                    recorder.record(kind, label, "ok", None, {}, _elapsed_ms(self.started))
                return False

        return _Timer()


def _build_dossier(
    payload: CopilotRequest,
    user: CurrentUserResponse,
    enabled_tools: set[str] | None = None,
) -> tuple[dict, dict, dict | None]:
    """Só dado real, e só do escopo que o usuário pode ver."""
    dossier: dict = {}
    context: dict = {"surface": payload.surface}
    expert = getattr(payload, "expert", None) or _expert_from_message(getattr(payload, "message", ""))
    if expert:
        context["expert"] = expert
    task_row = None

    with connect() as conn:
        if payload.task_id:
            task_row = tasks_repo.get_task(conn, payload.task_id)
            if not task_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada.")
            comments = tasks_repo.list_task_comments(conn, payload.task_id, True)
            dossier["task"] = {
                "title": task_row["title"],
                "status": task_row["status"],
                "group_status": task_row["group_status"],
                "priority": task_row.get("priority"),
                "start_date": task_row.get("start_date"),
                "due_date": task_row.get("due_date"),
                "description": (task_row.get("description") or "")[:2000],
                "acceptance_criteria": (task_row.get("acceptance_criteria") or "")[:2000],
                "definition_of_done": (task_row.get("definition_of_done") or "")[:2000],
            }
            dossier["task_comments"] = [
                {"author": row.get("author_name"), "body": row["body"][:600]} for row in comments[-10:]
            ]
            context["task_id"] = str(payload.task_id)

        if payload.workspace_id:
            client = workspaces_repo.find_accessible_client(
                conn, payload.workspace_id, is_platform_admin(user), user.id
            )
            if not client:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
            context["workspace_id"] = str(client["workspace_id"])
            context["client_name"] = client["name"]

        if payload.project_id:
            project = conn.execute(
                "select id, workspace_id, name, code, status, objective from projects where id = %s",
                (payload.project_id,),
            ).fetchone()
            if not project or (payload.workspace_id and project["workspace_id"] != payload.workspace_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
            dossier["project"] = dict(project)
            context["project_id"] = str(project["id"])

        if payload.opportunity_id:
            opportunity = proposals_repo.get_opportunity(conn, payload.opportunity_id)
            if not opportunity or (
                payload.workspace_id and opportunity.get("workspace_id") != payload.workspace_id
            ):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade não encontrada.")
            dossier["opportunity"] = {
                key: opportunity.get(key)
                for key in (
                    "id", "workspace_id", "title", "description", "budget_text", "fit_score",
                    "fit_analysis", "status", "next_action_at", "updated_at",
                )
            }
            dossier["commercial_timeline"] = proposals_repo.list_commercial_activities(
                conn, payload.opportunity_id
            )[:30]
            context["opportunity_id"] = str(payload.opportunity_id)

        if payload.proposal_id:
            proposal = conn.execute(
                """
                select id, workspace_id, opportunity_id, title, client_name, status,
                       executive_summary, pricing_cents, delivery_days, updated_at
                from commercial_proposals where id = %s and archived_at is null
                """,
                (payload.proposal_id,),
            ).fetchone()
            if not proposal or (payload.workspace_id and proposal["workspace_id"] != payload.workspace_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposta não encontrada.")
            dossier["proposal"] = dict(proposal)
            context["proposal_id"] = str(payload.proposal_id)

        # "O que priorizar hoje" precisa das tarefas da pessoa, não da carteira toda.
        my_tasks = tasks_repo.list_my_tasks(conn, user.id, is_platform_admin(user))
        dossier["my_tasks"] = [
            {
                "title": row["title"],
                "status": row["status"],
                "due_date": row.get("due_date"),
                "workspace": row.get("workspace_name"),
                "overdue": bool(row.get("due_date") and _is_overdue(row["due_date"])),
            }
            for row in my_tasks[:40]
        ]
        summary = client_hub_repo.get_portfolio_summary(conn)
        dossier["portfolio"] = {
            "overdue_deliverables": summary["overdue_deliverables"],
            "clients_at_risk": summary["clients_at_risk"],
            "pending_approvals": len(summary["pending_approvals"]),
            "stale_connections": len(summary["stale_connections"]),
            "radar_prospects_awaiting": summary["radar_prospects_awaiting"],
        }

        # Memória persistente (global da EG + do workspace, quando há um em
        # contexto) e skills já aprovadas — é o que faz o copiloto não perguntar
        # de novo o que já foi dito, e não redescobrir procedimento já resolvido.
        #
        # `list_memories_for_copilot`, não `list_memories`: aqui é o dossiê de UM
        # usuário, e preferência pessoal de outra pessoa não pode entrar. É a
        # consulta que faz "memória por natureza" (decisão do Eduardo,
        # 2026-08-04) valer na prática, não só existir no schema.
        workspace_uuid = payload.workspace_id
        memories = memory_repo.list_memories_for_copilot(conn, workspace_uuid, user.id)
        dossier["memories"] = [
            {
                "scope": "global" if row["workspace_id"] is None else "workspace",
                "category": row["category"],
                "title": row["title"],
                "body": row["body"],
                "authored_by_agent": row["authored_by"] is None,
                "personal": row["owner_user_id"] is not None,
            }
            for row in memories
        ]
        skills = memory_repo.list_skills(conn, workspace_uuid, include_global=True, status="approved")
        dossier["approved_skills"] = [
            {"name": row["name"], "description": row["description"], "procedure": row["procedure"]}
            for row in skills
        ]
        context["skill_ids_by_name"] = {row["name"]: str(row["id"]) for row in skills}

        # O que o produto JÁ TEM. Sem isso o copiloto propõe construir o que já
        # existe — ele conhecia as ações que pode executar, mas não as telas que
        # o Bioma oferece. É a diferença entre "não sei fazer isso" e "isso já
        # está em Operação EG → Radar Local".
        dossier["bioma_features"] = [
            {"key": key, "label": spec["label"], "description": spec["description"]}
            for key, spec in FEATURE_CATALOG.items()
        ]

        # Índice do conhecimento da EG — títulos, não conteúdo. O copiloto passa
        # a saber que a resposta existe e onde; puxar o texto inteiro de tudo
        # estouraria o contexto sem melhorar a resposta.
        dossier["knowledge_index"] = (
            knowledge_repo.list_doc_titles(conn)
            if enabled_tools is None or "search_knowledge_base" in enabled_tools
            else []
        )
    return dossier, context, task_row


def _is_overdue(value) -> bool:
    if isinstance(value, datetime):
        reference = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return reference < datetime.now(timezone.utc)
    if isinstance(value, date):
        return value < date.today()
    return False


def _expert_from_message(message: str) -> str | None:
    first = message.lstrip().split(maxsplit=1)[0] if message.strip() else ""
    if first.startswith("@") and len(first) > 1:
        return first[1:81]
    return None


def _response_blocks(
    answer: str,
    actions: list[CopilotAction],
    sources: list[CopilotSource],
    context: dict,
) -> list[CopilotBlock]:
    """Transforma saída já validada em componentes do catálogo seguro."""
    blocks = [
        CopilotBlock(
            id="answer",
            kind="markdown",
            data={"text": answer},
            source_refs=[source.reference for source in sources],
        )
    ]
    entity = next(
        (
            (kind, context.get(f"{kind}_id"))
            for kind in ("opportunity", "proposal", "project", "task", "workspace")
            if context.get(f"{kind}_id")
        ),
        None,
    )
    if entity:
        blocks.append(
            CopilotBlock(
                id=f"context-{entity[0]}",
                kind="entity_summary",
                title="Contexto ativo",
                data={"entity_type": entity[0], "entity_id": entity[1]},
            )
        )
    if actions:
        blocks.append(
            CopilotBlock(
                id="actions",
                kind="action_list",
                title="Ações",
                data={"items": [action.model_dump(mode="json") for action in actions]},
            )
        )
    if sources:
        blocks.append(
            CopilotBlock(
                id="sources",
                kind="source_list",
                title="Fontes",
                data={"items": [source.model_dump() for source in sources]},
            )
        )
    return blocks


def _execute(
    name: str,
    spec: dict,
    params: dict,
    why: str,
    task_row: dict | None,
    user: CurrentUserResponse,
    workspace_id=None,
) -> CopilotAction:
    """Executa ação reversível e devolve como desfazer."""

    def done(detail: str, undo: str | None = None) -> CopilotAction:
        return CopilotAction(
            name=name, label=spec["label"], params=params, why=why,
            status="executed", detail=detail, undo_hint=undo,
        )

    def failed(detail: str) -> CopilotAction:
        return CopilotAction(
            name=name, label=spec["label"], params=params, why=why,
            status="failed", detail=detail,
        )

    if name in ("summarize_thread", "answer_only"):
        return done("Nada foi alterado.")

    if name == "remember_fact":
        category = params.get("category")
        title = (params.get("title") or "").strip()
        body = (params.get("body") or "").strip()
        if category not in ("fact", "preference", "directive") or not title or not body:
            return failed("Categoria, título e conteúdo são obrigatórios para guardar na memória.")
        with connect() as conn:
            memory_repo.create_memory(
                conn, workspace_id, category, title[:200], body[:4000], None,
                "Escrito pelo copiloto durante a conversa.",
                # Preferência é sempre de quem está na conversa — "responda sem
                # introdução" não pode virar regra pra EG inteira porque uma
                # pessoa pediu. Fato/diretriz seguem compartilhados
                # (`create_memory` ignora este argumento fora de `preference`).
                owner_user_id=user.id if category == "preference" else None,
            )
        scope = "só para você" if category == "preference" else ("deste workspace" if workspace_id else "global da EG")
        return done(f'Memória "{title}" guardada ({scope}).', "Arquive a memória na tela de memórias para desfazer.")

    if name == "request_improvement":
        title = (params.get("title") or "").strip()
        need = (params.get("need") or "").strip()
        if not title or not need:
            return failed("Título e necessidade são obrigatórios para registrar a melhoria.")
        with connect() as conn:
            improvement_repo.create(
                conn,
                {
                    "workspace_id": workspace_id,
                    "title": title[:200],
                    "need": need[:4000],
                    "evidence": (params.get("evidence") or why or "")[:4000] or None,
                    "client_deliverable": bool(params.get("client_deliverable")),
                    # NULL = proposta pelo copiloto, não digitada por alguém.
                    "proposed_by": None,
                },
            )
        destino = "entrega do cliente" if params.get("client_deliverable") else "melhoria interna"
        return done(
            f'Necessidade "{title}" registrada como {destino} — aguardando sua revisão.',
            "Rejeite na fila de melhorias para descartar.",
        )

    if name == "propose_skill":
        skill_name = (params.get("name") or "").strip()
        description = (params.get("description") or "").strip()
        procedure = (params.get("procedure") or "").strip()
        if not skill_name or not description or not procedure:
            return failed("Nome, descrição e procedimento são obrigatórios para propor uma skill.")
        with connect() as conn:
            memory_repo.create_skill(
                conn, workspace_id, skill_name[:120], description[:300], procedure[:6000], None, why[:2000] or None
            )
        return done(
            f'Skill "{skill_name}" proposta — aguardando aprovação de um admin EG.',
            "Rejeite a skill na fila de revisão para descartar.",
        )

    if name == "capture_opportunity":
        title = (params.get("title") or "").strip()
        description = (params.get("description") or "").strip()
        if not title or not description:
            return failed("Título e descrição são obrigatórios para criar a oportunidade.")
        with connect() as conn:
            commercial_workspace_id = workspace_id
            if commercial_workspace_id is None:
                organization_id = _eg_organization_id(user)
                workspace = conn.execute(
                    """
                    select id from workspaces
                    where status = 'active' and kind = 'agency_internal'
                      and (subject_organization_id = %s or tenant_organization_id = %s)
                    order by created_at
                    limit 1
                    """,
                    (organization_id, organization_id),
                ).fetchone()
                commercial_workspace_id = workspace["id"] if workspace else None
            created = proposals_repo.create_opportunity(
                conn,
                {
                    "workspace_id": commercial_workspace_id,
                    "owner_user_id": user.id,
                    "source_platform": (params.get("source_platform") or "manual")[:50],
                    "external_id": params.get("external_id"),
                    "title": title[:255],
                    "url": params.get("url"),
                    "description": description[:10_000],
                    "budget_text": (params.get("budget_text") or "")[:100] or None,
                    "fit_score": None,
                    "fit_analysis": None,
                    "status": "new",
                    "raw_payload": {"captured_via": "copilot"},
                },
            )
            proposals_repo.create_commercial_activity(
                conn,
                created["id"],
                {
                    "activity_type": "captured",
                    "title": "Oportunidade capturada pela conversa",
                    "body": description[:20_000],
                    "source_kind": "copilot",
                    "idempotency_key": f"copilot-capture:{created['id']}",
                    "metadata": {"expert": "Propostas"},
                },
                user.id,
            )
        params["opportunity_id"] = str(created["id"])
        return done(
            f'Oportunidade "{title}" criada e ligada à continuidade comercial.',
            "Arquive a oportunidade para desfazer sem apagar o histórico.",
        )

    if not task_row:
        return failed("Esta ação exige uma tarefa em contexto.")

    task_id = task_row["id"]

    if name == "create_subtasks":
        titles = [str(title).strip() for title in (params.get("titles") or []) if str(title).strip()]
        if not titles:
            return failed("Nenhum título de subtarefa foi proposto.")
        with connect() as conn:
            for title in titles[:20]:
                tasks_repo.add_subtask(conn, task_id, title[:300])
        return done(
            f"{len(titles[:20])} subtarefa(s) criada(s).",
            "Remova pelo checklist da tarefa para desfazer.",
        )

    if name == "set_due_date":
        raw = params.get("due_date")
        if not raw:
            return failed("Data de vencimento não informada.")
        previous = task_row.get("due_date")
        with connect() as conn:
            tasks_repo.update_task(conn, task_id, {"due_date": raw})
        return done(
            f"Prazo alterado para {raw}.",
            f"Prazo anterior: {previous or 'sem prazo'}.",
        )

    if name == "set_status":
        new_status = params.get("status")
        if not new_status:
            return failed("Status não informado.")
        previous = task_row["status"]
        with connect() as conn:
            tasks_repo.update_task(conn, task_id, {"status": new_status})
        return done(f"Status alterado para {new_status}.", f"Status anterior: {previous}.")

    if name == "add_comment":
        body = (params.get("body") or "").strip()
        if not body:
            return failed("Comentário vazio.")
        with connect() as conn:
            # Comentário do copiloto nasce interno e assinado: quem lê a thread
            # precisa saber que aquilo não foi digitado por uma pessoa.
            tasks_repo.create_task_comment(
                conn,
                task_id,
                user.id,
                f"{body}\n\n_(via copiloto)_",
                False,
            )
        return done("Comentário publicado (interno).", "Exclua o comentário na tarefa para desfazer.")

    return failed("Ação sem execução implementada.")


def catalog_for(surface: str, user: CurrentUserResponse) -> list[dict]:
    """Catálogo da superfície — alimenta o menu de `/` na interface."""
    catalog = copilot_action_catalog()
    allowed = _allowed_actions(surface, _enabled_harness_tools(user))
    return [
        {
            "name": name,
            "label": catalog[name]["label"],
            "description": catalog[name]["description"],
            "requires_confirmation": not catalog[name]["reversible"],
        }
        for name in allowed
        if name in catalog
    ]
