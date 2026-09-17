import json
from datetime import datetime, timezone
from typing import Any

import httpx

AGENT_NAME_BY_PILAR = {
    "oferta": "Oferta Copywriter & Strategist",
    "demanda": "Paid Media & Growth Agent",
    "conversao": "Sales Closer & Script Agent",
    "onboarding": "Client Onboarding Strategist",
    "planning": "Multi-discipline Project Planner",
    "opportunity_fit": "Opportunity Fit Analyst",
    "content_retrospective": "Content Retrospective Analyst",
    "content_script": "Content Scriptwriter",
}

PILAR_INSTRUCTIONS = {
    "oferta": (
        "Você é o agente de Oferta da EverGreen. Analise a proposta de valor, o mecanismo único e a "
        "ancoragem de preço do briefing fornecido e produza uma revisão de copy de oferta irresistível, "
        "com bônus e garantia condicional coerentes com o contexto recebido."
    ),
    "demanda": (
        "Você é o agente de Demanda (Paid Media & Growth) da EverGreen. Avalie público-alvo, criativos e "
        "canais de distribuição (Meta/Google Ads) do briefing fornecido e estruture uma campanha com "
        "públicos e variações de anúncio de alta retenção."
    ),
    "conversao": (
        "Você é o agente de Conversão (Sales Closer & Script) da EverGreen. Mapeie o pipeline comercial do "
        "briefing fornecido e produza um script de fechamento e uma sequência de follow-up via WhatsApp que "
        "quebre as objeções mais prováveis."
    ),
    "onboarding": (
        "Você é o agente de onboarding da EverGreen. A partir da empresa, website e módulos contratados, "
        "produza um diagnóstico inicial estritamente baseado no contexto recebido, descreva o tom de voz "
        "apenas quando houver evidência e proponha entregas concretas para kickoff. Não invente fatos."
    ),
    "planning": (
        "Você é o planejador operacional da EverGreen. Converta contrato, escopo, briefing e documentos "
        "em um plano versionável para o projeto informado. Em Tech, produza tarefas acionáveis e testáveis, "
        "separando implementação, QA, validação e release; apenas technical_task pode ser candidata ao GitHub. "
        "Em Growth, diferencie entregas finitas de ciclos recorrentes, revisão e dependências. Em Social Media, "
        "trate 1 conteúdo como 1 entrega e respeite social_approval_flow, sem impor aprovação prévia da ideia "
        "quando o cliente só aprova depois da produção. Não invente escopo, preço, prazo ou evidência."
    ),
    "opportunity_fit": (
        "Você avalia aderência de uma oportunidade de projeto/vaga ao inventário de competências e ao time da "
        "EverGreen, estritamente a partir do contexto fornecido (título, descrição, orçamento, competências "
        "disponíveis, perfis do time). Dê uma nota de 0 a 100 (fit_score) e explique o porquê em fit_analysis, "
        "citando competências que casam (matched_skills) e gaps reais (skill_gaps). Não infira dados que não "
        "estão no contexto e não infle a nota — uma vaga genérica ou com poucas evidências deve pontuar baixo."
    ),
    "content_retrospective": (
        "Você analisa o histórico recente de conteúdo orgânico publicado (posts, legendas, transcrições e "
        "métricas reais de alcance/engajamento) fornecido no contexto. Identifique temas que performaram bem "
        "e mal, formatos recomendados, e extraia os ganchos (abertura/primeiras frases) que mais geraram "
        "resultado e os que falharam, sempre citando os post_ids como evidência. Não invente posts, métricas "
        "ou padrões que não estejam no contexto — se os dados forem insuficientes, diga isso na síntese em "
        "vez de generalizar."
    ),
    "content_script": (
        "Você é o roteirista-chefe de conteúdo da EverGreen. A partir da retrospectiva de performance, do "
        "banco de ganchos que já funcionou, do contexto de calendário/mercado e do benchmark de concorrentes "
        "fornecidos no contexto, gere um lote de roteiros completos de vídeo prontos para gravação — sem pedir "
        "briefing adicional ao usuário. Cada roteiro deve justificar o tema escolhido citando a evidência "
        "(retrospectiva, data comemorativa ou gancho reaproveitado) usada para escolhê-lo. Não repita o mesmo "
        "gancho ou tema em roteiros diferentes do mesmo lote. Não invente dado de mercado que não esteja no "
        "contexto."
    ),
}

OUTPUT_SCHEMA_OFERTA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "mecanismo_unico", "bonus_stack", "garantia", "recomendacao_regua"],
    "properties": {
        "headline": {"type": "string"},
        "mecanismo_unico": {"type": "string"},
        "bonus_stack": {"type": "array", "items": {"type": "string"}},
        "garantia": {"type": "string"},
        "recomendacao_regua": {"type": "string"},
    },
}

OUTPUT_SCHEMA_DEMANDA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["estrutura_campanha", "publicos_alvo", "variacoes_ads", "orcamento_sugerido_diario_cents"],
    "properties": {
        "estrutura_campanha": {"type": "string"},
        "publicos_alvo": {"type": "array", "items": {"type": "string"}},
        "variacoes_ads": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["hook", "format"],
                "properties": {"hook": {"type": "string"}, "format": {"type": "string"}},
            },
        },
        "orcamento_sugerido_diario_cents": {"type": "integer"},
    },
}

OUTPUT_SCHEMA_CONVERSAO = {
    "type": "object",
    "additionalProperties": False,
    "required": ["script_fechamento", "sequencia_whatsapp", "quebra_objecoes"],
    "properties": {
        "script_fechamento": {"type": "string"},
        "sequencia_whatsapp": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["dia", "mensagem"],
                "properties": {"dia": {"type": "integer"}, "mensagem": {"type": "string"}},
            },
        },
        "quebra_objecoes": {
            "type": "object",
            "additionalProperties": False,
            "required": ["esta_caro", "preciso_pensar"],
            "properties": {"esta_caro": {"type": "string"}, "preciso_pensar": {"type": "string"}},
        },
    },
}

OUTPUT_SCHEMA_ONBOARDING = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "company_summary",
        "tone_of_voice",
        "kickoff_recommendations",
        "initial_deliverables",
    ],
    "properties": {
        "company_summary": {"type": "string"},
        "tone_of_voice": {"type": "string"},
        "kickoff_recommendations": {"type": "array", "items": {"type": "string"}},
        "initial_deliverables": {"type": "array", "items": {"type": "string"}},
    },
}

OUTPUT_SCHEMA_PLANNING = {
    "type": "object",
    "additionalProperties": False,
    "required": ["plan_title", "objective", "assumptions", "items"],
    "properties": {
        "plan_title": {"type": "string"},
        "objective": {"type": ["string", "null"]},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_scope_item_id",
                    "phase_name",
                    "title",
                    "description",
                    "item_kind",
                    "due_offset_days",
                    "client_visible",
                    "approval_required",
                    "github_eligible",
                ],
                "properties": {
                    "source_scope_item_id": {"type": ["string", "null"]},
                    "phase_name": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "item_kind": {
                        "type": "string",
                        "enum": ["milestone", "deliverable", "content", "campaign", "technical_task"],
                    },
                    "due_offset_days": {"type": ["integer", "null"]},
                    "client_visible": {"type": "boolean"},
                    "approval_required": {"type": "boolean"},
                    "github_eligible": {"type": "boolean"},
                },
            },
        },
    },
}

OUTPUT_SCHEMA_OPPORTUNITY_FIT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["fit_score", "fit_analysis", "matched_skills", "skill_gaps", "recommendation"],
    "properties": {
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "fit_analysis": {"type": "string"},
        "matched_skills": {"type": "array", "items": {"type": "string"}},
        "skill_gaps": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string", "enum": ["prioritize", "review", "skip"]},
    },
}

OUTPUT_SCHEMA_CONTENT_RETROSPECTIVE = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "themes_performantes", "themes_fracos", "formatos_recomendados",
        "hooks_que_funcionam", "hooks_que_nao_funcionam", "sintese",
    ],
    "properties": {
        "themes_performantes": {"type": "array", "items": {"type": "string"}},
        "themes_fracos": {"type": "array", "items": {"type": "string"}},
        "formatos_recomendados": {"type": "array", "items": {"type": "string"}},
        "hooks_que_funcionam": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["hook_text", "padrao", "post_ids", "por_que_funciona"],
                "properties": {
                    "hook_text": {"type": "string"},
                    "padrao": {"type": "string"},
                    "post_ids": {"type": "array", "items": {"type": "string"}},
                    "por_que_funciona": {"type": "string"},
                },
            },
        },
        "hooks_que_nao_funcionam": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["hook_text", "post_ids", "por_que_nao_funciona"],
                "properties": {
                    "hook_text": {"type": "string"},
                    "post_ids": {"type": "array", "items": {"type": "string"}},
                    "por_que_nao_funciona": {"type": "string"},
                },
            },
        },
        "sintese": {"type": "string"},
    },
}

OUTPUT_SCHEMA_CONTENT_SCRIPT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["roteiros"],
    "properties": {
        "roteiros": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "titulo", "tema", "gancho_abertura", "roteiro_completo",
                    "formato_sugerido", "cta", "justificativa",
                ],
                "properties": {
                    "titulo": {"type": "string"},
                    "tema": {"type": "string"},
                    "gancho_abertura": {"type": "string"},
                    "roteiro_completo": {"type": "string"},
                    "formato_sugerido": {"type": "string"},
                    "cta": {"type": "string"},
                    "justificativa": {"type": "string"},
                },
            },
        },
    },
}

OUTPUT_SCHEMA_BY_PILAR = {
    "oferta": OUTPUT_SCHEMA_OFERTA,
    "demanda": OUTPUT_SCHEMA_DEMANDA,
    "conversao": OUTPUT_SCHEMA_CONVERSAO,
    "onboarding": OUTPUT_SCHEMA_ONBOARDING,
    "planning": OUTPUT_SCHEMA_PLANNING,
    "opportunity_fit": OUTPUT_SCHEMA_OPPORTUNITY_FIT,
    "content_retrospective": OUTPUT_SCHEMA_CONTENT_RETROSPECTIVE,
    "content_script": OUTPUT_SCHEMA_CONTENT_SCRIPT,
}


def execute_squad_pipeline(
    pilar: str,
    squad_name: str,
    input_data: dict[str, Any],
    settings,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Executa a esteira de agentes autônomos do Pilar EG (Oferta, Demanda ou Conversão).

    Sem OPENAI_API_KEY configurada no worker, cai numa prévia local honesta
    (generation_mode="preview", zero tokens/custo) em vez de fabricar números —
    mesmo padrão de bioma_worker.ai_content.generate_content.
    """
    agent_name = AGENT_NAME_BY_PILAR.get(pilar, "Agent")
    logs = [_log("Orchestrator", f"Iniciando Squad '{squad_name}' para o pilar de {pilar.upper()}...")]

    if not settings.openai_api_key:
        logs.append(_log(agent_name, "OPENAI_API_KEY não configurada; gerando prévia local determinística."))
        output = _preview_output(pilar, squad_name, input_data)
        logs.append(_log("FinOps Tracker", "Prévia local: 0 tokens, custo zero."))
        return {
            "output_data": output,
            "generation_mode": "preview",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "estimated_cost_cents": 0,
            "execution_logs": logs,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    logs.append(_log(agent_name, "Consultando o modelo de linguagem com o briefing fornecido..."))
    schema = OUTPUT_SCHEMA_BY_PILAR[pilar]
    payload = {
        "model": settings.openai_model,
        "instructions": PILAR_INSTRUCTIONS[pilar],
        "input": json.dumps({"squad_name": squad_name, "pilar": pilar, "input_data": input_data}, ensure_ascii=False),
        "text": {"format": {"type": "json_schema", "name": f"bioma_squad_{pilar}", "strict": True, "schema": schema}},
        "max_output_tokens": 6000 if pilar == "planning" else 2000,
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    owns_client = http_client is None
    client = http_client or httpx.Client(base_url="https://api.openai.com", timeout=settings.openai_request_timeout_seconds)
    try:
        response = client.post("/v1/responses", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
    finally:
        if owns_client:
            client.close()

    output = json.loads(_output_text(response_data))
    usage_raw = response_data.get("usage") or {}
    prompt_tokens = usage_raw.get("input_tokens", 0)
    completion_tokens = usage_raw.get("output_tokens", 0)
    total_tokens = usage_raw.get("total_tokens", prompt_tokens + completion_tokens)
    estimated_cost_cents = max(1, int((total_tokens / 1000) * 1.5)) if total_tokens else 0

    logs.append(_log(agent_name, f"Resposta recebida e validada contra o schema de {pilar}."))
    logs.append(_log(
        "FinOps Tracker",
        f"Execução concluída. Total Tokens: {total_tokens} (Custo Est.: {estimated_cost_cents} centavos).",
    ))

    return {
        "output_data": output,
        "generation_mode": "live",
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "estimated_cost_cents": estimated_cost_cents,
        "execution_logs": logs,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def _log(agent: str, message: str) -> dict[str, str]:
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "agent": agent, "message": message}


def _output_text(response_data: dict[str, Any]) -> str:
    if isinstance(response_data.get("output_text"), str):
        return response_data["output_text"]
    for item in response_data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise RuntimeError("A resposta do provedor não contém output_text.")


def _preview_output(pilar: str, squad_name: str, input_data: dict[str, Any]) -> dict[str, Any]:
    objective = input_data.get("objective") or squad_name

    if pilar == "oferta":
        return {
            "headline": f"Prévia local — oferta para: {objective}",
            "mecanismo_unico": "Configure OPENAI_API_KEY no worker para gerar o mecanismo único real.",
            "bonus_stack": ["Prévia local: bônus será gerado pelo modelo quando a chave estiver configurada."],
            "garantia": "Garantia a definir pelo modelo em execução live.",
            "recomendacao_regua": "Configure OPENAI_API_KEY para recomendação real de próximo teste.",
        }
    if pilar == "demanda":
        return {
            "estrutura_campanha": f"Prévia local — campanha para: {objective}",
            "publicos_alvo": ["Prévia local: públicos serão definidos pelo modelo em execução live."],
            "variacoes_ads": [{"hook": "Configure OPENAI_API_KEY para ganchos reais.", "format": "a definir"}],
            "orcamento_sugerido_diario_cents": 0,
        }
    if pilar == "onboarding":
        company_name = input_data.get("company_name") or input_data.get("objective") or "novo cliente"
        return {
            "company_summary": f"Prévia local para {company_name}; nenhuma varredura externa foi executada.",
            "tone_of_voice": "A confirmar no kickoff; configure OPENAI_API_KEY para análise assistida do contexto.",
            "kickoff_recommendations": [
                "Validar objetivos, responsáveis e critérios de aceite.",
                "Confirmar acessos e documentos necessários.",
            ],
            "initial_deliverables": [
                "Reunião de kickoff",
                "Coletar acessos e credenciais",
                "Briefing e diagnóstico inicial",
                "Definir cronograma e escopo",
            ],
        }
    if pilar == "planning":
        discipline = input_data.get("discipline") or "general"
        project_name = input_data.get("project_name") or objective
        scope_items = input_data.get("scope_items") or []
        approval_flow = input_data.get("social_approval_flow") or "adaptive"
        if not scope_items:
            scope_items = [{
                "id": None,
                "title": input_data.get("project_objective") or f"Planejar execução de {project_name}",
                "description": input_data.get("briefing"),
                "cadence": "one_off",
                "acceptance_required": True,
                "client_visible": True,
            }]

        phase_by_discipline = {
            "tech": "Implementação",
            "growth": "Execução e otimização",
            "social": "Planejamento e produção editorial",
            "general": "Execução",
        }
        kind_by_discipline = {
            "tech": "technical_task",
            "growth": "campaign",
            "social": "content",
            "general": "deliverable",
        }
        items = []
        for index, scope in enumerate(scope_items):
            items.append({
                "source_scope_item_id": scope.get("id"),
                "phase_name": phase_by_discipline.get(discipline, "Execução"),
                "title": scope.get("title") or f"Entrega {index + 1}",
                "description": scope.get("description"),
                "item_kind": kind_by_discipline.get(discipline, "deliverable"),
                "due_offset_days": None,
                "client_visible": scope.get("client_visible", True),
                "approval_required": scope.get("acceptance_required", True),
                "github_eligible": discipline == "tech",
            })
        validation_phase = {
            "tech": "QA, validação e release",
            "growth": "Revisão de resultados",
            "social": "Aprovação, publicação e análise",
            "general": "Validação",
        }.get(discipline, "Validação")
        items.append({
            "source_scope_item_id": None,
            "phase_name": validation_phase,
            "title": "Validar critérios de aceite e registrar resultado",
            "description": "Checkpoint explícito antes de considerar o ciclo concluído.",
            "item_kind": "milestone",
            "due_offset_days": None,
            "client_visible": True,
            "approval_required": True,
            "github_eligible": False,
        })
        assumptions = ["Prévia local determinística; revise o plano antes de aprovar."]
        if discipline == "social":
            assumptions.append(f"Fluxo de aprovação social selecionado: {approval_flow}.")
        return {
            "plan_title": f"Plano de execução — {project_name}",
            "objective": input_data.get("project_objective"),
            "assumptions": assumptions,
            "items": items,
        }
    if pilar == "opportunity_fit":
        return _preview_opportunity_fit(input_data)
    if pilar == "content_retrospective":
        return _preview_content_retrospective(input_data)
    if pilar == "content_script":
        return {
            "roteiros": [{
                "titulo": "Prévia local — configure OPENAI_API_KEY",
                "tema": "A definir pelo modelo em execução live.",
                "gancho_abertura": "Prévia local: o gancho real vem da retrospectiva quando a chave estiver configurada.",
                "roteiro_completo": "Configure OPENAI_API_KEY no worker para gerar roteiros reais a partir da retrospectiva e do banco de ganchos.",
                "formato_sugerido": "a definir",
                "cta": "a definir",
                "justificativa": "Prévia local determinística; nenhum roteiro foi de fato gerado.",
            }],
        }
    return {
        "script_fechamento": f"Prévia local — script para: {objective}",
        "sequencia_whatsapp": [{"dia": 1, "mensagem": "Configure OPENAI_API_KEY para a sequência real."}],
        "quebra_objecoes": {
            "esta_caro": "Prévia local: resposta será gerada pelo modelo em execução live.",
            "preciso_pensar": "Prévia local: resposta será gerada pelo modelo em execução live.",
        },
    }


def _preview_opportunity_fit(input_data: dict[str, Any]) -> dict[str, Any]:
    # Sem OPENAI_API_KEY, não fabricamos uma nota "alta por padrão" — aplicamos a
    # mesma heurística transparente de palavras-chave já usada na ingestão
    # (services/proposals.py), determinística e auditável, nunca enviesada pra cima.
    title = str(input_data.get("opportunity_title") or "").lower()
    description = str(input_data.get("opportunity_description") or "").lower()
    full_text = f"{title} {description}"
    inventory = [str(s).lower() for s in (input_data.get("agency_skills_inventory") or [])]

    score = 50
    matched_skills = [skill for skill in inventory if skill and skill in full_text]
    score += len(matched_skills) * 7

    known_tech_keywords = ["marketo", "salesforce", "magento", "shopify", "activecampaign", "klaviyo", "pipedrive"]
    skill_gaps = [tech for tech in known_tech_keywords if tech in full_text and tech not in inventory]
    score -= len(skill_gaps) * 10

    fit_score = min(98, max(25, score))
    recommendation = "prioritize" if fit_score >= 70 else "review" if fit_score >= 45 else "skip"
    return {
        "fit_score": fit_score,
        "fit_analysis": (
            "Prévia local (heurística de palavras-chave, não é avaliação de IA real — "
            "configure OPENAI_API_KEY no worker para análise contextual genuína)."
        ),
        "matched_skills": matched_skills,
        "skill_gaps": [gap.capitalize() for gap in skill_gaps],
        "recommendation": recommendation,
    }


def _preview_content_retrospective(input_data: dict[str, Any]) -> dict[str, Any]:
    # Sem OPENAI_API_KEY não classificamos "tema" ou "padrão de gancho" — isso
    # exige compreensão real de linguagem. O que dá pra fazer honestamente é
    # ordenar os posts reais por alcance real e mostrar a abertura literal de
    # cada um, deixando claro que a leitura de padrão ainda depende do modelo.
    posts = input_data.get("posts") or []
    ranked = [p for p in posts if (p.get("reach") or 0) > 0]
    ranked.sort(key=lambda p: p.get("reach") or 0, reverse=True)
    top = ranked[:3]
    bottom = ranked[-3:] if len(ranked) > 3 else []

    def opening(post: dict[str, Any]) -> str:
        text = post.get("transcript") or post.get("caption") or ""
        words = str(text).strip().split()
        return " ".join(words[:15]) or "(sem legenda ou transcrição)"

    hooks_ok = [
        {
            "hook_text": opening(post),
            "padrao": "Prévia local: classificação de padrão exige OPENAI_API_KEY.",
            "post_ids": [str(post.get("post_id"))],
            "por_que_funciona": f"Maior alcance real do período ({post.get('reach', 0)}).",
        }
        for post in top
    ]
    hooks_bad = [
        {
            "hook_text": opening(post),
            "post_ids": [str(post.get("post_id"))],
            "por_que_nao_funciona": f"Menor alcance real do período ({post.get('reach', 0)}).",
        }
        for post in bottom
    ]

    if not posts:
        sintese = "Prévia local: nenhum post encontrado no período para retrospectiva."
    else:
        sintese = (
            f"Prévia local — ordenação determinística por alcance real de {len(posts)} post(s), não é "
            "análise de IA. Configure OPENAI_API_KEY no worker para identificar padrões reais de tema, "
            "formato e gancho."
        )

    return {
        "themes_performantes": ["Prévia local: temas reais exigem OPENAI_API_KEY."] if posts else [],
        "themes_fracos": [],
        "formatos_recomendados": [],
        "hooks_que_funcionam": hooks_ok,
        "hooks_que_nao_funcionam": hooks_bad,
        "sintese": sintese,
    }
