"""Resumo diário do cockpit — decisão 3.

Você escolheu a opção A: **um card no cockpit ao abrir, sem push por evento**.
O motivo de ser um card e não uma notificação está na própria decisão: push por
evento vira ruído, e ruído vira gente que ignora o canal inteiro.

Duas regras que este módulo existe para garantir:

1. **Dia limpo não inventa assunto.** Um resumo que fala todo dia, mesmo sem
   nada, treina a pessoa a fechar sem ler — e aí ele para de funcionar
   justamente no dia em que tem algo.
2. **A ordem é por custo de não agir, não por quantidade.** Entrega atrasada já
   quebrou um combinado; conexão velha degrada dado que ninguém olha hoje.
   Ordenar por contagem colocaria 40 conexões antes de 1 entrega atrasada.

Função pura: recebe o que o cockpit já apurou e devolve as linhas. Sem banco,
sem rede, sem LLM — o resumo não é redação, é leitura.
"""

from typing import Any

# Quantos exemplos citar por linha. O card é um RESUMO: listar tudo o
# transformaria na própria tela que ele deveria resumir.
MAX_EXEMPLOS = 3


def compose_brief(summary: dict[str, Any]) -> dict[str, Any]:
    """Monta as linhas do resumo a partir do apanhado do cockpit."""
    atrasadas = list(summary.get("overdue_items") or [])
    aprovacoes = list(summary.get("pending_approvals") or [])
    conexoes = list(summary.get("stale_connections") or [])
    prospects = int(summary.get("radar_prospects_awaiting") or 0)
    em_risco = int(summary.get("clients_at_risk") or 0)

    itens: list[dict[str, Any]] = []

    # A ordem desta lista É a prioridade. Cliente em risco primeiro porque é o
    # único item cujo desfecho ruim é perder a conta.
    if em_risco:
        itens.append(
            _linha(
                "client_risk",
                "critical",
                f"{em_risco} cliente{'s' if em_risco > 1 else ''} em risco",
                "Sinal de churn no rollup da carteira.",
                em_risco,
                [],
                "/clientes",
            )
        )

    if atrasadas:
        itens.append(
            _linha(
                "overdue",
                "critical",
                f"{len(atrasadas)} entrega{'s' if len(atrasadas) > 1 else ''} "
                f"atrasada{'s' if len(atrasadas) > 1 else ''}",
                "Prazo combinado já passou.",
                len(atrasadas),
                [item.get("title", "") for item in atrasadas],
                "/operacao/tarefas",
            )
        )

    if aprovacoes:
        itens.append(
            _linha(
                "approval",
                "warning",
                f"{len(aprovacoes)} item{'ns' if len(aprovacoes) > 1 else ''} "
                f"esperando aprovação",
                "Parado até alguém decidir.",
                len(aprovacoes),
                [item.get("title", "") for item in aprovacoes],
                "/eg-propostas",
            )
        )

    if conexoes:
        itens.append(
            _linha(
                "stale_connection",
                "warning",
                f"{len(conexoes)} conexão{'ões' if len(conexoes) > 1 else ''} sem sincronizar",
                "As métricas dessas contas estão envelhecendo.",
                len(conexoes),
                [item.get("provider", "") for item in conexoes],
                "/configuracoes",
            )
        )

    if prospects:
        # `info`, não alarme: prospect esperando é FILA, não falha. Marcar como
        # crítico junto com entrega atrasada apagaria a diferença entre as duas.
        itens.append(
            _linha(
                "radar",
                "info",
                f"{prospects} prospect{'s' if prospects > 1 else ''} aguardando no Radar",
                "Oportunidade parada na fila.",
                prospects,
                [],
                "/operacao/radar-local",
            )
        )

    return {"clear": not itens, "items": itens}


def _linha(
    kind: str,
    severity: str,
    title: str,
    detail: str,
    count: int,
    examples: list[str],
    href: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "severity": severity,
        "title": title,
        "detail": detail,
        "count": count,
        "examples": [texto for texto in examples if texto][:MAX_EXEMPLOS],
        # Resumo sem destino vira notícia. Toda linha tem que poder ser clicada.
        "href": href,
    }
