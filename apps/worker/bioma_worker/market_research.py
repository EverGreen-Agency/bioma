import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx


REFINEMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["sector_interpretation", "assumptions", "focus_options"],
    "properties": {
        "sector_interpretation": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "focus_options": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["key", "label", "description"],
                "properties": {
                    "key": {"type": "string"},
                    "label": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
    },
}


def _string_array() -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}}


def _object_array(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": required,
            "properties": properties,
        },
    }


REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "executive_summary",
        "market_overview",
        "commercial_process",
        "challenges",
        "market_leaders",
        "terminology",
        "growth_opportunities",
        "prospecting_playbook",
        "content_opportunities",
        "caveats",
        "sources",
    ],
    "properties": {
        "title": {"type": "string"},
        "executive_summary": {"type": "string"},
        "market_overview": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "description",
                "market_size_and_segments",
                "business_models",
                "growth_outlook",
                "trends",
                "source_urls",
            ],
            "properties": {
                "description": {"type": "string"},
                "market_size_and_segments": _string_array(),
                "business_models": _string_array(),
                "growth_outlook": {"type": "string"},
                "trends": _string_array(),
                "source_urls": _string_array(),
            },
        },
        "commercial_process": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "sales_strategies",
                "acquisition_and_retention",
                "buying_journey",
                "qualification_signals",
                "source_urls",
            ],
            "properties": {
                "sales_strategies": _string_array(),
                "acquisition_and_retention": _string_array(),
                "buying_journey": _string_array(),
                "qualification_signals": _string_array(),
                "source_urls": _string_array(),
            },
        },
        "challenges": _object_array(
            {
                "challenge": {"type": "string"},
                "business_impact": {"type": "string"},
                "opportunity": {"type": "string"},
                "source_urls": _string_array(),
            },
            ["challenge", "business_impact", "opportunity", "source_urls"],
        ),
        "market_leaders": _object_array(
            {
                "name": {"type": "string"},
                "segment": {"type": "string"},
                "success_strategy": {"type": "string"},
                "source_urls": _string_array(),
            },
            ["name", "segment", "success_strategy", "source_urls"],
        ),
        "terminology": _object_array(
            {
                "term": {"type": "string"},
                "definition": {"type": "string"},
                "source_urls": _string_array(),
            },
            ["term", "definition", "source_urls"],
        ),
        "growth_opportunities": _object_array(
            {
                "opportunity": {"type": "string"},
                "recommended_service": {"type": "string"},
                "rationale": {"type": "string"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                "source_urls": _string_array(),
            },
            ["opportunity", "recommended_service", "rationale", "priority", "source_urls"],
        ),
        "prospecting_playbook": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "opening_angles",
                "qualification_questions",
                "likely_objections",
                "credibility_cautions",
            ],
            "properties": {
                "opening_angles": _string_array(),
                "qualification_questions": _string_array(),
                "likely_objections": _string_array(),
                "credibility_cautions": _string_array(),
            },
        },
        "content_opportunities": _object_array(
            {
                "theme": {"type": "string"},
                "recommended_format": {"type": "string"},
                "funnel_stage": {
                    "type": "string",
                    "enum": ["awareness", "consideration", "decision", "retention"],
                },
                "rationale": {"type": "string"},
                "source_urls": _string_array(),
            },
            ["theme", "recommended_format", "funnel_stage", "rationale", "source_urls"],
        ),
        "caveats": _string_array(),
        "sources": _object_array(
            {
                "url": {"type": "string"},
                "title": {"type": ["string", "null"]},
                "publisher": {"type": ["string", "null"]},
                "publication_date": {"type": ["string", "null"]},
            },
            ["url", "title", "publisher", "publication_date"],
        ),
    },
}


REFINEMENT_INSTRUCTIONS = """
Você interpreta setores para uma pesquisa de mercado da EverGreen.
Não faça a pesquisa completa nesta etapa. Desambigue o setor e proponha entre
5 e 8 recortes concretos que o usuário possa selecionar. Os recortes devem
cobrir, quando aplicável, segmentos, modelo comercial, regulação, geografia,
tipo de comprador e maturidade da operação. Não invente fatos; explicite
hipóteses em assumptions. As chaves devem usar apenas a-z, 0-9 e underscore.
""".strip()


REPORT_INSTRUCTIONS = """
Você é o pesquisador de mercado da EverGreen. Use a busca web para produzir
uma pesquisa atual, técnica e útil para prospecção consultiva, Growth e Social
Media. Priorize fontes primárias e oficiais, depois associações setoriais,
relatórios reconhecidos e veículos especializados. Compare datas e regiões.

Regras obrigatórias:
- não invente tamanho de mercado, líder, regulação, tendência ou fonte;
- se a evidência for insuficiente, registre a limitação em caveats;
- cada bloco factual deve listar em source_urls apenas URLs realmente usadas;
- diferencie fato observado, inferência e recomendação;
- converta oportunidades em serviços EG sem forçar aderência;
- inclua perguntas de qualificação e cuidados de credibilidade para cold calls;
- gere oportunidades editoriais reutilizáveis por Growth e Social Media;
- não inclua segredos, dados pessoais ou alegações sem evidência.
""".strip()


def refine_market_sector(
    request: dict[str, Any],
    settings,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "output": _preview_refinement(request),
            "generation_mode": "preview",
            "provider": "local_preview",
            "model": "market-refinement-preview-v1",
            "response_id": None,
            "token_usage": _empty_usage(),
            "estimated_cost_cents": None,
        }

    payload = {
        "model": settings.openai_research_model,
        "instructions": REFINEMENT_INSTRUCTIONS,
        "input": json.dumps(request, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bioma_market_refinement",
                "strict": True,
                "schema": REFINEMENT_SCHEMA,
            }
        },
        "max_output_tokens": 1600,
        "store": False,
    }
    response_data = _post_response(payload, settings, http_client)
    return {
        "output": json.loads(_output_text(response_data)),
        "generation_mode": "live",
        "provider": "openai",
        "model": settings.openai_research_model,
        "response_id": response_data.get("id"),
        "token_usage": _usage(response_data),
        "estimated_cost_cents": None,
    }


def generate_market_research(
    request: dict[str, Any],
    settings,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        report = _preview_report(request)
        return {
            "report": report,
            "sources": [],
            "generation_mode": "preview",
            "provider": "local_preview",
            "model": "market-research-preview-v1",
            "response_id": None,
            "token_usage": _empty_usage(),
            "estimated_cost_cents": None,
        }

    payload = {
        "model": settings.openai_research_model,
        "instructions": REPORT_INSTRUCTIONS,
        "input": json.dumps(
            {
                **request,
                "current_date": datetime.now(timezone.utc).date().isoformat(),
                "service_context": [
                    "growth e mídia paga",
                    "landing pages e CRO",
                    "CRM, automações e BI",
                    "treinamento comercial",
                    "conteúdo para Instagram e LinkedIn",
                ],
            },
            ensure_ascii=False,
        ),
        "tools": [
            {
                "type": "web_search",
                "search_context_size": "high",
                "user_location": {
                    "type": "approximate",
                    "country": "BR",
                    "timezone": "America/Sao_Paulo",
                },
            }
        ],
        "include": ["web_search_call.action.sources"],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bioma_market_research",
                "strict": True,
                "schema": REPORT_SCHEMA,
            }
        },
        "reasoning": {"effort": "medium"},
        "max_output_tokens": 12000,
        "store": False,
    }
    response_data = _post_response(payload, settings, http_client)
    report = json.loads(_output_text(response_data))
    sources = _collect_sources(response_data, report.get("sources", []))
    trusted_urls = {source["url"] for source in sources}
    report = _filter_report_source_urls(report, trusted_urls)
    report["sources"] = sources
    return {
        "report": report,
        "sources": sources,
        "generation_mode": "live",
        "provider": "openai",
        "model": settings.openai_research_model,
        "response_id": response_data.get("id"),
        "token_usage": _usage(response_data),
        # Custos de tokens e da ferramenta variam por modelo/conta. O dashboard
        # registra unidades e marca custo desconhecido em vez de estimar errado.
        "estimated_cost_cents": None,
    }


def _post_response(payload: dict[str, Any], settings, http_client: httpx.Client | None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    owns_client = http_client is None
    client = http_client or httpx.Client(
        base_url="https://api.openai.com",
        timeout=settings.openai_request_timeout_seconds,
    )
    try:
        response = client.post("/v1/responses", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    finally:
        if owns_client:
            client.close()


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


def _usage(response_data: dict[str, Any]) -> dict[str, int]:
    raw = response_data.get("usage") or {}
    input_tokens = int(raw.get("input_tokens") or 0)
    output_tokens = int(raw.get("output_tokens") or 0)
    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": int(raw.get("total_tokens") or input_tokens + output_tokens),
    }


def _empty_usage() -> dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _valid_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    return value if parsed.scheme in ("http", "https") and parsed.netloc else None


def _collect_sources(response_data: dict[str, Any], declared_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_url: dict[str, dict[str, Any]] = {}

    def remember(value: dict[str, Any]) -> None:
        url = _valid_url(value.get("url"))
        if not url:
            return
        current = by_url.setdefault(
            url,
            {
                "url": url,
                "title": None,
                "publisher": None,
                "publication_date": None,
                "consulted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        for key in ("title", "publisher", "publication_date"):
            if value.get(key) and not current.get(key):
                current[key] = value[key]

    for item in response_data.get("output", []):
        if item.get("type") == "web_search_call":
            for source in (item.get("action") or {}).get("sources", []):
                remember(source)
        if item.get("type") == "message":
            for content in item.get("content", []):
                for annotation in content.get("annotations", []):
                    citation = annotation.get("url_citation") or annotation
                    if annotation.get("type") == "url_citation" or citation.get("url"):
                        remember(citation)

    provider_urls = set(by_url)
    for source in declared_sources:
        url = _valid_url(source.get("url"))
        if not url:
            continue
        # A declaração do modelo só complementa metadados de uma URL observada
        # na saída nativa da ferramenta; nunca cria evidência por conta própria.
        if url not in provider_urls:
            continue
        remember(source)

    return list(by_url.values())


def _filter_report_source_urls(report: dict[str, Any], trusted_urls: set[str]) -> dict[str, Any]:
    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: (
                    [url for url in item if url in trusted_urls]
                    if key == "source_urls" and isinstance(item, list)
                    else clean(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return clean(report)


def _preview_refinement(request: dict[str, Any]) -> dict[str, Any]:
    sector = request["sector"].strip()
    geography = request.get("geographic_scope") or "Brasil"
    return {
        "sector_interpretation": (
            f"Prévia local para {sector}, com recorte geográfico em {geography}. "
            "Nenhuma pesquisa externa foi executada."
        ),
        "assumptions": [
            "Os recortes são genéricos até a execução com OPENAI_API_KEY.",
            "Valide se o setor é B2B, B2C ou híbrido antes de gerar o relatório.",
        ],
        "focus_options": [
            {"key": "market_structure", "label": "Estrutura e segmentos", "description": "Tamanho, cadeia de valor e principais recortes do mercado."},
            {"key": "business_models", "label": "Modelos de negócio", "description": "Receitas, margens, recorrência e estrutura operacional."},
            {"key": "commercial_process", "label": "Processo comercial", "description": "Aquisição, qualificação, venda, retenção e pós-venda."},
            {"key": "regulation", "label": "Regulação e riscos", "description": "Normas, barreiras, dependências e cuidados de credibilidade."},
            {"key": "competition", "label": "Concorrência e referências", "description": "Líderes, diferenciação e estratégias observáveis."},
            {"key": "growth_social", "label": "Growth e Social Media", "description": "Oportunidades de campanhas, conteúdo e automações."},
        ],
    }


def _preview_report(request: dict[str, Any]) -> dict[str, Any]:
    sector = request["sector"]
    focus_labels = [item["label"] for item in request.get("selected_focus", [])]
    unavailable = "Configure OPENAI_API_KEY para executar pesquisa web com fontes verificáveis."
    return {
        "title": f"Prévia de pesquisa de mercado — {sector}",
        "executive_summary": (
            f"Estrutura do relatório para {sector}. Esta é uma prévia local e não contém fatos de mercado."
        ),
        "market_overview": {
            "description": unavailable,
            "market_size_and_segments": focus_labels or ["Recortes a confirmar"],
            "business_models": ["A pesquisar"],
            "growth_outlook": unavailable,
            "trends": ["A pesquisar"],
            "source_urls": [],
        },
        "commercial_process": {
            "sales_strategies": ["A pesquisar"],
            "acquisition_and_retention": ["A pesquisar"],
            "buying_journey": ["A pesquisar"],
            "qualification_signals": ["A validar com evidências"],
            "source_urls": [],
        },
        "challenges": [{
            "challenge": "Pesquisa externa não executada",
            "business_impact": "Não é possível afirmar dores reais do setor nesta prévia.",
            "opportunity": "Executar a versão live antes de usar em prospecção.",
            "source_urls": [],
        }],
        "market_leaders": [],
        "terminology": [],
        "growth_opportunities": [],
        "prospecting_playbook": {
            "opening_angles": [],
            "qualification_questions": ["Quais recortes deste setor refletem o ICP desejado?"],
            "likely_objections": [],
            "credibility_cautions": ["Não use esta prévia como evidência de mercado."],
        },
        "content_opportunities": [],
        "caveats": [
            "Prévia local determinística.",
            "Nenhuma busca web, validação factual ou fonte foi consultada.",
        ],
        "sources": [],
    }
