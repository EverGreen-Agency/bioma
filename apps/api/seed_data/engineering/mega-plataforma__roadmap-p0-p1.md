# Roadmap P0-P1 - Bioma

**Data:** 2026-07-07  
**Status:** proposta de sequenciamento  
**Regra:** modulo so vai para codigo com spec + ADRs criticos aprovados.

## P0 - Fundacao em producao

### `mod-multitenant`

Objetivo: autenticação, organizações, tenants, RBAC, RLS, audit logs e superfície mínima autenticada.

Estado: em engenharia.  
Gate de saída:

- Auth Supabase funcionando.
- Organizações/tenants com isolamento RLS.
- RBAC mínimo.
- Audit log.
- Sem dependência operacional do `/dashboard` antigo.

## P0.5 - Guardrails antes de cliente/BI

Estes módulos não devem virar produto grande agora. Eles são guardrails para o restante não nascer frágil.

| Ordem | Módulo | Por que antes da Fase 1 | ADR principal |
|---:|---|---|---|
| 1 | `mod-observabilidade` | sem isso, falha de integração/API/job vira surpresa do cliente | `ADR-0001-observabilidade-stack.md` |
| 2 | `cofre-senhas` | hoje acessos podem estar em planilha; BI/Ads/Hub dependem disso | `ADR-0001-vault-secrets.md` |
| 3 | `mod-integrations-hub` | evita OAuth/webhook/token duplicado por módulo | `ADR-0001-contrato-integracoes.md` |
| 4 | `mod-workflows-aprovacoes` | mantém HITL real para ações sensíveis | `ADR-0001-motor-aprovacoes.md` |
| 5 | `mod-lgpd-governanca-dados` | define classificação, retenção e uso de IA com dados sensíveis | `ADR-0001-governanca-dados.md` |

Gate de saída P0.5:

- Credenciais não são mais coletadas por planilha para fluxos novos críticos.
- Integrações têm status, dono, escopo e erro visível.
- Ações sensíveis têm approval request server-side.
- Dados sensíveis têm classificação mínima.
- Logs/alertas básicos existem para app, DB, filas e integrações.

## P1 - Primeira camada visível

Só iniciar ADRs/código depois dos guardrails mínimos acima:

1. `client-hub`
2. `mod-bi-dashboards`
3. `mod-entrega-mkt`

ADRs P1 planejados em `adrs-fase-1-planejados.md`.

