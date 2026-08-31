# Spec: mod-policy-research

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-policy-research`, `mod-radar-pesquisa`, `mod-comunicacao-wpp`, `mod-bi-dashboards`, `mod-entrega-mkt`

## 1. Objetivo

Monitorar e transformar mudanças de políticas, APIs e regras de plataformas críticas em alertas e decisões operacionais para a EG.

## 2. Contexto

Meta, Google, WhatsApp, LinkedIn, plataformas de ads, APIs e políticas de IA mudam com frequência. Isso afeta cobrança, janela de mensagem, banimento, OAuth, métricas, automações e entregas.

## 3. Escopo

- Monitoramento curado de fontes oficiais e confiáveis.
- Registro de mudança, data, impacto e módulos afetados.
- Alertas para squads/módulos.
- Insumos para ADRs e revisão de playbooks.

## 4. Fora de Escopo

- Monitorar todas as notícias do mercado.
- Tomar decisão automática de stack.
- Usar fonte sem data/proveniência.

## 5. Requisitos Funcionais

- RF1 — Mudança deve ter fonte, data, resumo e impacto.
- RF2 — Sistema deve mapear módulos afetados.
- RF3 — Mudança crítica deve gerar tarefa/alerta.
- RF4 — Histórico deve permitir ver quando uma política mudou.

## 6. Requisitos Não-Funcionais

- **Fonte:** priorizar documentação oficial.
- **Atualidade:** informação precisa de validade temporal.
- **Ação:** toda mudança crítica deve ter owner.

## 7. Critérios de Aceite

- CA1 — Mudança de política Meta/Google gera registro rastreável.
- CA2 — Módulo afetado aparece na mudança.
- CA3 — Alerta crítico tem owner e próxima ação.

## 8. Riscos e Dependências

- **Risco:** decisão baseada em informação desatualizada.  
  **Mitigação:** data, fonte e revisão periódica.

- **Dependência:** `mod-radar-pesquisa`.
- **Dependência:** `mod-observabilidade`.

