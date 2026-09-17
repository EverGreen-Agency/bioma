"""Tradução de propostas comerciais.

Traduz o `content_markdown` inteiro (não os campos fragmentados como
`scope_offer`/`scope_conversion`) — é o que a pessoa de fato lê, e um blob de
texto preserva títulos e listas sem precisar reconstruir estrutura depois.

Sem `OPENAI_API_KEY` levanta em vez de gerar prévia local: uma tradução falsa
que parece traduzida é pior que nenhuma — quem lê não tem como saber que o
texto foi inventado, ao contrário de uma prévia rotulada em outras partes do
Bioma.
"""

from __future__ import annotations

from typing import Any
import json

import httpx

INSTRUCTIONS = """Você traduz uma proposta comercial para uso interno da equipe da EverGreen.

Regras:
- Traduza o SENTIDO, não palavra por palavra — o texto tem que soar natural
  para quem fala o idioma de destino.
- Preserve a formatação Markdown (títulos, listas, negrito) exatamente como
  está — só o texto muda, a estrutura não.
- Nomes próprios (nome do cliente, marcas, produtos) não são traduzidos.
- Números, preços, prazos e datas não mudam.
- Se algum trecho já estiver no idioma de destino, deixe como está — não
  precisa "retraduzir" o que já serve."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "content_markdown"],
    "properties": {
        "title": {"type": "string"},
        "content_markdown": {"type": "string"},
    },
}


def translate_proposal(payload: dict[str, Any], settings, http_client: httpx.Client | None = None) -> dict[str, Any]:
    """`payload`: `{title, content_markdown, target_language}`.

    Devolve `{output: {title, content_markdown}, usage, provider, model}`.
    Levanta `RuntimeError` sem chave — ver docstring do módulo.
    """
    if not settings.openai_api_key:
        raise RuntimeError("Tradução exige OPENAI_API_KEY: esta decisão não aceita prévia local.")

    request_payload = {
        "model": settings.openai_model,
        "instructions": INSTRUCTIONS,
        "input": json.dumps(
            {
                "target_language": payload["target_language"],
                "title": payload["title"],
                "content_markdown": payload["content_markdown"],
            },
            ensure_ascii=False,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bioma_proposal_translation",
                "strict": True,
                "schema": SCHEMA,
            }
        },
        "max_output_tokens": 4000,
        "store": False,
    }

    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    owns_client = http_client is None
    client = http_client or httpx.Client(
        base_url="https://api.openai.com", timeout=settings.openai_request_timeout_seconds
    )
    try:
        response = client.post("/v1/responses", headers=headers, json=request_payload)
        response.raise_for_status()
        response_data = response.json()
    finally:
        if owns_client:
            client.close()

    output = json.loads(_output_text(response_data))
    usage = response_data.get("usage") or {}
    return {
        "output": output,
        "generation_mode": "live",
        "provider": "openai",
        "model": settings.openai_model,
        "usage": {
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
        },
    }


def _output_text(response_data: dict[str, Any]) -> str:
    for item in response_data.get("output", []):
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text":
                return content["text"]
    raise RuntimeError("Resposta do modelo sem texto estruturado.")
