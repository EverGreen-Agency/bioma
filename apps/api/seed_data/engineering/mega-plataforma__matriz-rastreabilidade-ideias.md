# Matriz de Rastreabilidade de Ideias - Mega Plataforma EG / Bioma

**Data:** 2026-07-07  
**Status:** rascunho de cobertura, nao aprovacao de engenharia  
**Objetivo:** mapear onde cada ideia/modulo relevante da Mega Plataforma esta documentado e separar o que ja tem spec, o que e decisao/doutrina, o que e spin-off e o que ainda precisa de registro no Banco de Ideias.

## 1. Specs de Modulos da Plataforma

| Ideia / modulo | Artefato | Status |
|---|---|---|
| `mod-nucleo` | `_opensquad/_memory/engenharia/mod-nucleo/spec.md` | rascunho |
| `mod-multitenant` | `_opensquad/_memory/engenharia/mod-multitenant/spec.md` + ADRs | em producao / fundacao |
| `mod-cockpit-interno` | `_opensquad/_memory/engenharia/mod-cockpit-interno/spec.md` | rascunho completo |
| `client-hub` | `_opensquad/_memory/engenharia/client-hub/spec.md` | rascunho completo |
| `mod-bi-dashboards` | `_opensquad/_memory/engenharia/mod-bi-dashboards/spec.md` | rascunho completo |
| `mod-comercial` | `_opensquad/_memory/engenharia/mod-comercial/spec.md` | rascunho completo |
| `mod-entrega-mkt` | `_opensquad/_memory/engenharia/mod-entrega-mkt/spec.md` | rascunho completo |
| `mod-conhecimento` | `_opensquad/_memory/engenharia/mod-conhecimento/spec.md` | rascunho completo |
| `mod-conhecimento-video` | `_opensquad/_memory/engenharia/mod-conhecimento-video/spec.md` | rascunho futuro |
| `mod-financeiro` | `_opensquad/_memory/engenharia/mod-financeiro/spec.md` | rascunho completo |
| `mod-contratos` | `_opensquad/_memory/engenharia/mod-contratos/spec.md` | rascunho completo |
| `mod-juridico` | `_opensquad/_memory/engenharia/mod-juridico/spec.md` | rascunho futuro |
| `mod-observabilidade` | `_opensquad/_memory/engenharia/mod-observabilidade/spec.md` | rascunho completo |
| `mod-comunicacao-wpp` | `_opensquad/_memory/engenharia/mod-comunicacao-wpp/spec.md` | rascunho completo |
| `mod-logistica-kits` | `_opensquad/_memory/engenharia/mod-logistica-kits/spec.md` | rascunho completo |
| `mod-rh` | `_opensquad/_memory/engenharia/mod-rh/spec.md` | rascunho completo |
| `mod-certificacoes` | `_opensquad/_memory/engenharia/mod-certificacoes/spec.md` | rascunho futuro |
| `mod-saas-billing` | `_opensquad/_memory/engenharia/mod-saas-billing/spec.md` | rascunho completo |
| `mod-site-cms` | `_opensquad/_memory/engenharia/mod-site-cms/spec.md` | rascunho completo |
| `mod-mobile` | `_opensquad/_memory/engenharia/mod-mobile/spec.md` | rascunho futuro |
| `mod-workspace` | `_opensquad/_memory/engenharia/mod-workspace/spec.md` | rascunho baixa prioridade |
| `mod-marca-artefatos` | `_opensquad/_memory/engenharia/mod-marca-artefatos/spec.md` | rascunho completo |
| `mod-radar-pesquisa` | `_opensquad/_memory/engenharia/mod-radar-pesquisa/spec.md` | rascunho completo |
| `mod-policy-research` | `_opensquad/_memory/engenharia/mod-policy-research/spec.md` | rascunho completo |
| `squad-negocios` | `_opensquad/_memory/engenharia/squad-negocios/spec.md` | rascunho futuro |

## 2. Specs Transversais Adicionadas Nesta Revisao

| Ideia / modulo | Artefato | Observacao |
|---|---|---|
| `cofre-senhas` | `_opensquad/_memory/engenharia/cofre-senhas/spec.md` | em producao (fatia) no bioma/ /vault desde 2026-07-07 |
| `mod-integrations-hub` | `_opensquad/_memory/engenharia/mod-integrations-hub/spec.md` | proposta de modulo; registrar no Banco de Ideias se aprovado |
| `mod-workflows-aprovacoes` | `_opensquad/_memory/engenharia/mod-workflows-aprovacoes/spec.md` | proposta de modulo; generaliza `tag-ativacao` e aprovacoes HITL |
| `mod-lgpd-governanca-dados` | `_opensquad/_memory/engenharia/mod-lgpd-governanca-dados/spec.md` | proposta de modulo; governa consentimento, retencao, PII e uso de LLM externa |

## 3. Ideias Absorvidas por Specs

| Ideia | Absorvida por |
|---|---|
| `banco-ideias`, `banco-stack`, `banco-arquitetura`, `hub-chat-dispatcher`, `tag-ativacao`, `cross-repo-awareness`, `escritorio-virtual` | `mod-cockpit-interno` |
| `health-score`, `squad-raiox`, `selo-benchmark`, `aprovacao-tinder`, `marketplace-addons`, `delivery-tracker`, `gamificacao-setup`, `client-operating-agreement`, `exit-handover-mode` | `client-hub` |
| `ads-api-skills`, `squad-relatorios`, `narrative-reports` | `mod-bi-dashboards` / `mod-entrega-mkt` |
| `carteira-clientes`, `squad-prospector`, `squad-hunter`, `squad-reunioes`, `squad-onboarding`, `copilot-vendas`, `kommo-squad-dedup`, `centralizacao-comunicacoes`, `integ-google-meu-negocio`, `demo-tenant-sales-theater` | `mod-comercial` |
| `segundo-cerebro`, `vector-store`, `context-decay`, `stack-memoria-zep`, `squad-voz-cliente`, `dossie-provas`, `evidence-ledger`, `drive-rag-cliente`, `clonagem-personas` | `mod-conhecimento` |
| `ai-credits-metering`, `planejamento-negocios` | `mod-financeiro` / `squad-negocios` |
| `reseller-revenda-depth` | `mod-saas-billing` |
| `portfolio-sites-recursos` | `mod-site-cms` |
| `tech-scout`, `proveniencia-skills-mcp`, `absorver-opensource` | `mod-radar-pesquisa` |
| `access-request-portal` | `cofre-senhas` |
| `integration-doctor` | `mod-integrations-hub` |

## 4. Spin-offs / Separar

Continuam fora do core imediato do Bioma, salvo reaproveitamento de codigo ou aprendizado:

- `foton`
- `prisma-bi`
- `telecom-chips`
- `micro-aws-hosting`
- `educacao-comunidade`
- `trade-autonomo`
- `jogo-interno`
- `forward-deployed`

## 5. Doutrinas / Decisoes Comerciais

Nao sao specs de software por si so, mas regras de decisao que influenciam modulos:

- `precificacao-valor`
- `service-as-software`
- `ai-cmo-mrr`
- `dogfooding`
- `fabrica-back-front`
- `ia-adapta-cliente`
- `change-management`
- `decisao-bpo`
- `nome-plataforma`

## 6. Observacoes de Qualidade

- As specs desta matriz estao completas estruturalmente pelo template minimo: objetivo, contexto, escopo, fora de escopo, RF, RNF, criterios de aceite, riscos/dependencias.
- Completo estruturalmente nao significa aprovado para codigo. Antes de engenharia, cada modulo ainda precisa de ADRs criticos e aprovacao do Eduardo/Juiz.
- `mod-integrations-hub`, `mod-workflows-aprovacoes` e `mod-lgpd-governanca-dados` **já estão registrados** no `ideas.json` (confirmado 2026-07-07, nota anterior estava desatualizada).
- 2ª varredura da parte 1+2 (2026-07-07) encontrou +7 gaps agora capturados: `escada-oferta-tech`, `desvincular-opensquad`, `modulo-investimentos`, `banco-skills-produto`, `squad-ativacao-por-cliente`, `niveis-score-expandido`, `squad-recrutamento`. Banco em 148 ideias.
- O `/dashboard` antigo agora tem destino definido em `mod-cockpit-interno`: legado intencional, inventariar -> reaproveitar -> aposentar.
