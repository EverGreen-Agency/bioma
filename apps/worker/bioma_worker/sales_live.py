"""Análise ao vivo de reunião comercial — caminho dedicado.

Antes isto passava pelo squad genérico de conversão e o tipo da sugestão era
decidido por busca de palavra ("caro", "preço") na transcrição. Isso erra nos
dois sentidos: "não ficou caro" virava objeção de preço, e uma objeção de prazo
sem essas palavras virava "pergunta".

Aqui o modelo classifica o momento e devolve a fala sugerida em schema fechado,
com latência menor (um round-trip, prompt curto, janela recente só).

Sem OPENAI_API_KEY devolve uma leitura determinística e ROTULADA da janela — não
inventa análise: apenas aponta o que é observável (quem falou mais, se houve
pergunta em aberto) e diz que a IA não rodou.
"""

import json
from typing import Any

import httpx

LIVE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["moment", "suggested_line", "rationale", "signals", "next_question", "risk"],
    "properties": {
        "moment": {
            "type": "string",
            "enum": [
                "objection_price",
                "objection_timing",
                "objection_authority",
                "objection_trust",
                "buying_signal",
                "discovery_gap",
                "off_track",
                "closing_window",
            ],
        },
        "suggested_line": {"type": "string"},
        "rationale": {"type": "string"},
        "signals": {"type": "array", "items": {"type": "string"}},
        "next_question": {"type": "string"},
        "risk": {"type": "string"},
    },
}

INSTRUCTIONS = """
Você assiste um consultor da EverGreen DURANTE uma reunião comercial. Recebe a
janela mais recente da transcrição, os participantes e o contexto do cliente.

Responda como quem cochicha no ouvido: curto, aplicável agora.

Regras obrigatórias:
- `moment` classifica o que ACABOU de acontecer na janela; escolha objeção
  específica (preço, prazo, alçada, confiança) só quando houver evidência na
  fala — nunca por palavra isolada, e sim pelo sentido;
- `suggested_line` é a frase que o consultor pode falar agora, em português do
  Brasil, máximo 45 palavras, sem jargão e sem prometer resultado;
- `signals` lista o que o cliente sinalizou, citando o trecho que sustenta;
- `next_question` é UMA pergunta que destrava a conversa;
- `risk` é o erro mais provável do consultor neste momento;
- não invente número, prazo, preço ou fato sobre o cliente que não esteja no
  contexto recebido.
""".strip()

MOMENT_LABELS = {
    "objection_price": "objection_response",
    "objection_timing": "objection_response",
    "objection_authority": "objection_response",
    "objection_trust": "objection_response",
    "buying_signal": "next_step",
    "discovery_gap": "question",
    "off_track": "question",
    "closing_window": "next_step",
}


def analyze_live_window(
    request: dict[str, Any],
    settings,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "output": _preview_analysis(request),
            "generation_mode": "preview",
            "provider": "local_preview",
            "model": "sales-live-preview-v1",
        }

    payload = {
        "model": settings.openai_model,
        "instructions": INSTRUCTIONS,
        "input": json.dumps(
            {
                "objective": request.get("objective"),
                "meeting_title": request.get("title"),
                # Só a janela recente: a call inteira encareceria e pioraria a
                # latência sem melhorar a sugestão do momento.
                "recent_window": (request.get("transcript_window") or "")[-8_000:],
                "participants": request.get("participants") or [],
                "client_context": request.get("knowledge_context") or {},
            },
            ensure_ascii=False,
            default=str,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bioma_sales_live",
                "strict": True,
                "schema": LIVE_SCHEMA,
            }
        },
        "max_output_tokens": 700,
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
        "output": json.loads(_output_text(response_data)),
        "generation_mode": "live",
        "provider": "openai",
        "model": settings.openai_model,
    }


def suggestion_type_for(moment: str) -> str:
    """Traduz o momento classificado para o vocabulário de sugestão do copiloto."""
    return MOMENT_LABELS.get(moment, "question")


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


def _preview_analysis(request: dict[str, Any]) -> dict[str, Any]:
    """Leitura observável da janela, sem análise de IA e sem fingir que houve."""
    window = request.get("transcript_window") or ""
    lines = [line for line in window.splitlines() if line.strip()]
    open_question = any(line.rstrip().endswith("?") for line in lines[-3:])
    return {
        "moment": "discovery_gap",
        "suggested_line": (
            "Prévia local: nenhuma análise de IA foi executada. "
            "Configure OPENAI_API_KEY para receber a sugestão de fala."
        ),
        "rationale": "Prévia determinística — apenas o que é observável na janela.",
        "signals": [
            f"{len(lines)} fala(s) na janela recente.",
            "A última fala é uma pergunta em aberto." if open_question else "Nenhuma pergunta em aberto nas últimas falas.",
        ],
        "next_question": "Qual é o critério de decisão e quem participa dela?",
        "risk": "Seguir sem confirmar o próximo passo combinado.",
    }
