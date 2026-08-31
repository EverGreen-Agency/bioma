"""Insight multicanal a partir dos números reais de mídia paga.

Substitui um gerador que era só nome: as métricas vinham do banco (corretas),
mas as recomendações eram STRINGS FIXAS no código — "escalar criativos de maior
retenção nos primeiros 3s", "concentrar orçamento em C-Level" — que não mudavam
com o dado nenhum. A tela chamava aquilo de "IA Insight".

Aqui vale a mesma regra do briefing: sem `OPENAI_API_KEY`, devolve uma prévia
determinística que ORGANIZA os números (útil, e honesta sobre não ter sintetizado);
com chave, a IA sintetiza sob instrução de nunca afirmar nada que não esteja nos
números recebidos.

O que o modelo NÃO pode fazer, e está no prompt: inventar benchmark de mercado,
citar canal sem dado, ou recomendar ação que os números não sustentam. Um painel
de performance que sugere o que não observou é pior que um painel vazio.
"""

import json
from typing import Any

import httpx

INSIGHT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "insights"],
    "properties": {
        "summary": {"type": "string"},
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["channel", "title", "finding", "action_recommendation", "impact_level"],
                "properties": {
                    # `channel` fica livre para o modelo poder falar de
                    # "multichannel" quando a leitura for da soma, não de um
                    # canal isolado.
                    "channel": {"type": "string"},
                    "title": {"type": "string"},
                    "finding": {"type": "string"},
                    "action_recommendation": {"type": "string"},
                    "impact_level": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
    },
}

INSTRUCTIONS = """Você é analista de mídia paga da EverGreen, agência B2B brasileira.

Recebe números REAIS de investimento, leads e CPA por canal, já apurados. Sua
tarefa é ler esses números e escrever o que eles dizem.

Regras inegociáveis:
- Nunca afirme nada que os números não sustentem. Sem dado de um canal, não
  fale desse canal.
- Nunca cite benchmark de mercado, média do setor ou referência externa: você
  não tem essa informação e inventá-la é o pior erro possível aqui.
- Toda recomendação precisa apontar qual número a motivou. "Reduzir CPA" sem
  dizer qual CPA está alto não serve.
- Se os números forem insuficientes para uma conclusão, diga isso no summary em
  vez de preencher com genérico.
- `impact_level` reflete quanto dinheiro está em jogo, não seu entusiasmo.
- Português do Brasil, direto, sem jargão de marketing vazio.

Valores monetários chegam em CENTAVOS. Converta para reais ao escrever."""


def _preview_insight(totals: dict[str, Any]) -> dict[str, Any]:
    """Prévia sem modelo: organiza os números e diz que não houve síntese.

    Diferente do que existia antes, ela NÃO recomenda ação — porque recomendar
    sem análise é exatamente o que estava errado. Ela relata."""
    channels = totals.get("channels", [])
    total_spend = totals.get("total_spend_cents", 0)
    total_leads = totals.get("total_leads", 0)
    cpa = totals.get("overall_cpa_cents", 0)

    insights = [
        {
            "channel": channel["channel"],
            "title": f"{channel['label']} — números do período",
            "finding": (
                f"Investimento de R$ {channel['spend_cents'] / 100:,.2f} com "
                f"{channel['leads']} leads"
                + (f" (CPA de R$ {channel['cpa_cents'] / 100:,.2f})." if channel["leads"] else ", sem leads registrados.")
            ),
            "action_recommendation": (
                "Sem análise automática: a chave de IA não está configurada. "
                "Os números acima são reais e vieram da sincronização."
            ),
            "impact_level": "medium",
        }
        for channel in channels
    ]

    if not insights:
        insights.append(
            {
                "channel": "multichannel",
                "title": "Sem dado sincronizado no período",
                "finding": "Nenhum canal de mídia paga tem dado sincronizado para este workspace.",
                "action_recommendation": "Conecte as contas em Configurações → Empresa → Integrações e rode uma sincronização.",
                "impact_level": "medium",
            }
        )

    summary = (
        f"Prévia local (sem IA): R$ {total_spend / 100:,.2f} investidos, {total_leads} leads, "
        f"CPA consolidado de R$ {cpa / 100:,.2f}. "
        "Os números são reais; a síntese exige OPENAI_API_KEY configurada."
        if total_spend
        else "Prévia local (sem IA): nenhum investimento sincronizado no período."
    )
    return {"summary": summary, "insights": insights}


def _output_text(response_data: dict[str, Any]) -> str:
    for item in response_data.get("output", []):
        for block in item.get("content", []):
            if block.get("type") == "output_text":
                return block["text"]
    raise RuntimeError("Resposta da OpenAI sem texto estruturado.")


def generate_multichannel_insight(
    totals: dict[str, Any],
    settings,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "insight": _preview_insight(totals),
            "generation_mode": "preview",
            "provider": "local_preview",
            "model": "multichannel-preview-v1",
        }

    payload = {
        "model": settings.openai_model,
        "instructions": INSTRUCTIONS,
        "input": json.dumps(totals, ensure_ascii=False, default=str),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bioma_multichannel_insight",
                "strict": True,
                "schema": INSIGHT_SCHEMA,
            }
        },
        "max_output_tokens": 2000,
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
        "insight": json.loads(_output_text(response_data)),
        "generation_mode": "live",
        "provider": "openai",
        "model": settings.openai_model,
    }
