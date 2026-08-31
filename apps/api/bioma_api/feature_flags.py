"""Catálogo de features do Bioma e seus estados por cliente.

Distinção que importa (e que `enabled_modules` não resolve):

- **módulo** = o cliente contratou aquilo? (`enabled_modules`)
- **feature flag** = aquilo já está pronto para este cliente? (esta tabela)

Um cliente pode ter `analytics` contratado e ainda assim ver o Radar Local como
"em breve". São eixos ortogonais.

Estados:
- `hidden`      — não aparece em lugar nenhum
- `coming_soon` — aparece rotulado "Em breve", sem acesso (gera desejo e evita
                  a pergunta "vocês não têm isso?")
- `beta`        — acessível, rotulado como beta
- `active`      — normal

O default de cada feature vive AQUI, em código. Sem linha no banco, vale o
default — nenhuma feature depende de seed para existir.
"""

from typing import Literal

FeatureState = Literal["hidden", "coming_soon", "beta", "active"]

FEATURE_CATALOG: dict[str, dict[str, str]] = {
    "local_radar": {
        "label": "Radar Local",
        "description": "Prospecção de negócios locais via Google Maps com auditoria de presença.",
        "default_state": "active",
    },
    "copilot": {
        "label": "Copiloto",
        "description": "Assistente com ações reais dentro do Bioma.",
        "default_state": "beta",
    },
    "agent_memory": {
        "label": "Memória do copiloto",
        "description": "Memória persistente e procedimentos aprendidos pelo copiloto.",
        "default_state": "beta",
    },
    "briefing_draft": {
        "label": "Rascunho de briefing por IA",
        "description": "Monta o briefing a partir dos sinais já existentes do cliente.",
        "default_state": "active",
    },
    "script_scoreboard": {
        "label": "Placar de roteiros da IA",
        "description": "Compara desempenho dos roteiros gerados com o resto da conta.",
        "default_state": "active",
    },
    "sales_copilot": {
        "label": "Copiloto de vendas",
        "description": "Assistência ao vivo em reunião comercial, com transcrição.",
        "default_state": "beta",
    },
    "whatsapp_multiprovider": {
        "label": "WhatsApp multi-provedor",
        "description": "Envio e histórico de WhatsApp por Evolution API, Meta Cloud ou Z-API.",
        "default_state": "beta",
    },
    "portfolio_performance": {
        "label": "Rollup da carteira",
        "description": "Investimento por canal e leads de todos os clientes lado a lado.",
        "default_state": "active",
    },
}

VALID_STATES: tuple[FeatureState, ...] = ("hidden", "coming_soon", "beta", "active")


def default_state(feature_key: str) -> FeatureState:
    entry = FEATURE_CATALOG.get(feature_key)
    return entry["default_state"] if entry else "hidden"  # type: ignore[return-value]


def is_accessible(state: FeatureState) -> bool:
    """`coming_soon` aparece na interface mas NÃO libera acesso — é vitrine."""
    return state in ("beta", "active")
