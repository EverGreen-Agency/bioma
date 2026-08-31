"""Rascunho de briefing montado a partir de sinais reais já no Bioma.

Sem OPENAI_API_KEY, devolve uma prévia determinística que **organiza os sinais
coletados** (útil de verdade, só sem síntese) e diz o que não rodou. Com chave,
a IA sintetiza — mas sob instrução de nunca afirmar nada que não esteja no
dossiê, e de listar explicitamente o que falta descobrir na call.
"""

import json
from typing import Any

import httpx

BRIEFING_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary",
        "diagnosis",
        "hypotheses",
        "recommended_focus",
        "questions_for_client",
        "missing_data",
    ],
    "properties": {
        "summary": {"type": "string"},
        "diagnosis": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["observation", "evidence"],
                "properties": {
                    "observation": {"type": "string"},
                    "evidence": {"type": "string"},
                },
            },
        },
        "hypotheses": {"type": "array", "items": {"type": "string"}},
        "recommended_focus": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["focus", "rationale", "service"],
                "properties": {
                    "focus": {"type": "string"},
                    "rationale": {"type": "string"},
                    "service": {"type": "string"},
                },
            },
        },
        "questions_for_client": {"type": "array", "items": {"type": "string"}},
        "missing_data": {"type": "array", "items": {"type": "string"}},
    },
}

INSTRUCTIONS = """
Você é o estrategista da EverGreen montando o RASCUNHO de briefing de um cliente.
Receberá um dossiê com sinais reais coletados das integrações do Bioma (perfil
preenchido pelo time, mídia paga, orgânico do Instagram, presença em busca,
projetos contratados e, se houver, pesquisa de mercado do setor).

Regras obrigatórias:
- todo item de `diagnosis` precisa citar em `evidence` o número ou campo do
  dossiê que o sustenta; sem evidência no dossiê, o item vira `hypotheses`;
- fonte ausente é ausência, não problema: se o Instagram não está conectado,
  isso entra em `missing_data`, e não vira "o cliente não faz orgânico";
- `recommended_focus` só pode recomendar serviços dentro do escopo contratado
  quando houver projetos listados; fora disso, marque como oportunidade a validar;
- `questions_for_client` são as perguntas que o dossiê NÃO responde e que a
  próxima call precisa resolver — é a parte mais útil deste rascunho;
- português do Brasil, tom consultivo e direto, sem promessa de resultado.
""".strip()


def generate_briefing_draft(
    dossier: dict[str, Any],
    settings,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "draft": _preview_draft(dossier),
            "generation_mode": "preview",
            "provider": "local_preview",
            "model": "briefing-preview-v1",
        }

    payload = {
        "model": settings.openai_model,
        "instructions": INSTRUCTIONS,
        "input": json.dumps(dossier, ensure_ascii=False, default=str),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bioma_briefing_draft",
                "strict": True,
                "schema": BRIEFING_SCHEMA,
            }
        },
        "max_output_tokens": 3000,
        "store": False,
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    owns_client = http_client is None
    client = http_client or httpx.Client(
        base_url="https://api.openai.com",
        timeout=settings.openai_request_timeout_seconds,
    )
    try:
        response = client.post("/v1/responses", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
    finally:
        if owns_client:
            client.close()

    return {
        "draft": json.loads(_output_text(response_data)),
        "generation_mode": "live",
        "provider": "openai",
        "model": settings.openai_model,
    }


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


def _preview_draft(dossier: dict[str, Any]) -> dict[str, Any]:
    """Organiza os sinais reais sem sintetizar — o valor aqui é o dossiê, não a prosa."""
    signals = dossier.get("signals") or {}
    missing = dossier.get("missing_sources") or []
    diagnosis = []

    paid = signals.get("paid_media")
    if paid:
        diagnosis.append(
            {
                "observation": f"Mídia paga ativa: {paid.get('campaigns')} campanha(s) em 90 dias.",
                "evidence": (
                    f"{paid.get('impressions')} impressões, {paid.get('clicks')} cliques, "
                    f"{paid.get('conversions')} conversões (ads_campaign_daily)."
                ),
            }
        )
    social = signals.get("organic_social")
    if social:
        diagnosis.append(
            {
                "observation": f"Orgânico no Instagram com {social.get('posts')} posts em 90 dias.",
                "evidence": (
                    f"Alcance médio {round(float(social.get('avg_reach') or 0))}, "
                    f"engajamento médio {round(float(social.get('avg_engagement') or 0))}."
                ),
            }
        )
    search = signals.get("search_presence")
    if search:
        diagnosis.append(
            {
                "observation": f"Presença em busca com {search.get('queries')} termos gerando impressão.",
                "evidence": f"{search.get('clicks')} cliques em {search.get('impressions')} impressões (Search Console).",
            }
        )

    return {
        "summary": (
            f"Rascunho local para {dossier.get('client_name')}. Dossiê montado com "
            f"{len(diagnosis)} fonte(s) de dado real; a síntese de IA não foi executada "
            "(OPENAI_API_KEY não configurada)."
        ),
        "diagnosis": diagnosis,
        "hypotheses": [],
        "recommended_focus": [],
        "questions_for_client": [
            "Quais são as metas de faturamento e de lead para os próximos 90 dias?",
            "Qual canal o cliente considera prioritário hoje e por quê?",
            "Existe restrição de marca, tom ou tema que o time precisa respeitar?",
        ],
        "missing_data": missing
        + ["Síntese de IA não executada — este rascunho apenas organiza os sinais coletados."],
    }
