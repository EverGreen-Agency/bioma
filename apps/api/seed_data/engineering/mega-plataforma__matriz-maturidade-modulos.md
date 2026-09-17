# Matriz de Maturidade dos Modulos - Bioma

**Data:** 2026-07-07  
**Objetivo:** separar briefing, spec, ADR, aprovacao e execucao para evitar que rascunhos parecam prontos para codigo.

## Legenda

- **B0 - Captura:** ideia registrada, sem spec.
- **B1 - Briefing:** direcao escrita, ainda sem contrato de engenharia.
- **S1 - Spec rascunho completa:** tem escopo, fora de escopo, RF, RNF, aceite e riscos.
- **A1 - ADR pendente:** spec existe, mas decisoes tecnicas bloqueantes faltam.
- **A2 - ADR aceito:** decisoes criticas aprovadas.
- **E1 - Em engenharia:** pode codar ou ja esta codando.
- **FUT - Futuro/baixa prioridade:** documentado para nao se perder, mas fora do foco atual.

## Matriz

| Modulo | Fase | Maturidade | Proximo gate |
|---|---:|---|---|
| `mod-multitenant` | P0 | E1 | CONCLUIDO 2026-07-08 (em producao no bioma/, 53 testes CA1-CA7); manter ADRs atualizados |
| `mod-observabilidade` | P0.5 | E1 (fatia) | fatia em producao 2026-07-08 (health, incidents, DLQ->incidente, /viveiro/status); falta Sentry/BetterStack (conta/DPA) |
| `cofre-senhas` | P0.5 | E1 (fatia) | fatia em producao 2026-07-07 (/vault, AES-256-GCM, reveal auditado c/ auto-ocultar); proximos: rotacao guiada, access-request |
| `mod-integrations-hub` | P0.5 | S1/A1 | ADR OAuth/API keys/webhooks por provedor inicial |
| `mod-workflows-aprovacoes` | P0.5 | S1/A1 | ADR approval engine/HITL policy |
| `mod-lgpd-governanca-dados` | P0.5 | E1 (fatia) | fatia em producao 2026-07-08 (8 classes, purposes/consents, gate IA externa); PENDENTE: revisao juridica humana |
| `mod-nucleo` | P0.5 | S1 | consolidar contratos transversais apos ADRs P0.5 |
| `mod-cockpit-interno` | P1 interno | S1/A1 | ADR inventario/aposentadoria do `/dashboard` + arquitetura de adapters |
| `client-hub` | P1 | S1/A1 | ADR NFC/magic link + entitlements/service catalog |
| `mod-bi-dashboards` | P1 | S1/A1 | ADR build-vs-embed + estrategia ETL/historico |
| `mod-entrega-mkt` | P1/P2 | S1/A1 | ADR escrita em plataformas externas + QA/publicacao |
| `mod-comercial` | P2 | S1/A1 | ADR CRM proprio vs Kommo/Apollo |
| `mod-conhecimento` | P2 | S1/A1 | ADR pgvector vs dedicado + memoria/decay |
| `mod-financeiro` | P2 | S1/A1 | ADR fiscal/bancario + AI credits metering |
| `mod-contratos` | P2 | S1/A1 | ADR Autentique manter-vs-absorver |
| `mod-marca-artefatos` | P2 | S1/A1 | ADR Canva/Figma/geracao interna + direitos de assets |
| `mod-comunicacao-wpp` | P4 | S1/A1 | ADR Cloud API vs Evolution/Baileys |
| `mod-logistica-kits` | P2 | S1/A1 | ADR NFC/magic link compartilhado com client-hub |
| `mod-saas-billing` | P3 | S1/A1 | ADR Stripe vs Asaas/Iugu + profundidade reseller |
| `mod-site-cms` | P3 | S1/A1 | ADR CMS proprio vs headless externo |
| `mod-radar-pesquisa` | P2/P4 | S1 | integrar com Banco de Stack e ADRs |
| `mod-policy-research` | P4 | S1 | definir fontes oficiais e gatilhos |
| `mod-juridico` | P4 | S1/FUT | revisar com juridico antes de IA operacional |
| `mod-rh` | P4 | S1/FUT | esperar volume de equipe |
| `mod-certificacoes` | P4 | S1/FUT | depende de `mod-rh` |
| `mod-conhecimento-video` | P4 | S1/FUT | depende de direitos/consentimento |
| `mod-mobile` | P4 | S1/FUT | PWA primeiro, app nativo depois |
| `mod-workspace` | P4 | S1/FUT | possivel overreach; validar ROI |
| `squad-negocios` | paralelo | S1/FUT | usar para spin-offs e decisoes fora do core |

## Ordem recomendada de maturacao

1. **P0:** finalizar `mod-multitenant`.
2. **P0.5:** fechar ADRs de `mod-observabilidade`, `cofre-senhas`, `mod-integrations-hub`, `mod-workflows-aprovacoes`, `mod-lgpd-governanca-dados`.
3. **P1:** fechar ADRs de `client-hub`, `mod-bi-dashboards`, `mod-entrega-mkt`.
4. **P2:** backoffice EG: comercial, contratos, conhecimento, financeiro, marca.
5. **P3/P4:** billing/site e modulos amplos/futuros.

