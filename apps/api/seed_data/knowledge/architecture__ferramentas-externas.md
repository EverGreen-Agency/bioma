<!-- Inventário das ferramentas/serviços EXTERNOS que a EG usa ou paga. -->
<!-- Complementa arquitetura.md (que é só princípios/decisões). Aqui é o "o quê usamos". -->
<!-- Diferente do stack.json (Tech Radar de techs p/ CONSTRUIR): aqui são serviços que OPERAMOS/pagamos. -->
# Ferramentas & Arquitetura Externa da EG

> Registro vivo do que a EG **usa/assina hoje** + a **decisão** de cada uma na mega-plataforma (manter externo · absorver/construir interno · revender). Nasce da parte 1+2 do doc da Mega Plataforma (Eduardo pediu registrar o Autentique e a proveniência das ferramentas). Atualizado: 2026-07-07.

## Legenda de decisão
- **MANTER** — seguimos usando externo (a IA integra via API, não substitui).
- **ABSORVER** — construir versão interna na plataforma (vira módulo).
- **REVENDER** — hospedar/revender como fonte de renda (white-label/agency).
- **AVALIAR** — em pesquisa (ver `stack.json` anel `assess`).

## Operação / Backoffice
| Ferramenta | Uso hoje | Decisão | Módulo/nota |
|---|---|---|---|
| **Autentique** | Assinatura/gestão de contratos | ABSORVER (avaliar) | `mod-contratos` + `mod-juridico` (validar contrato×lei) |
| **Kommo** | CRM (WhatsApp, funil) | ABSORVER/AVALIAR | `mod-comercial`; falha de dedup a absorver (`kommo-squad-dedup`); alt: Attio/Assis (assess) |
| **ClickUp** | Gestão de tarefas/projetos | MANTER (integrar) | `mod-comercial`/onboarding; decidir se comunicação interna centraliza aqui (`centralizacao-comunicacoes`) |
| **Titan** | E-mail corporativo | AVALIAR/ABSORVER | `mod-workspace` (possível overreach — e-mail/drive/calendar próprios) |
| **Google Workspace** | Drive/Docs/Calendar (referência) | MANTER/absorver-parcial | `drive-rag-cliente` (drive próprio + RAG); `mod-workspace` |
| **NordPass (ref.)** | Cofre de senhas (hoje planilha!) | ABSORVER | `cofre-senhas` — acessos de cliente/funcionário |

## Marketing / Cliente
| Ferramenta | Uso hoje | Decisão | Módulo/nota |
|---|---|---|---|
| **Meta Business Manager / Ads** | Anúncios; parceiro na BM do cliente | MANTER (integrar) | `ads-api-skills`, `mod-bi-dashboards`; onboarding vira parceiro na BM |
| **Google Ads / MCC** | Anúncios; conta gerente | MANTER (integrar) | idem; `integ-google-meu-negocio` (GMB) pendente |
| **ManyChat** | Automação de funil no Insta | AVALIAR/REVENDER | `revenda-ferramentas` |
| **mLabs** | Relatórios social low-ticket | AVALIAR | referência p/ `mod-bi-dashboards` (social) |
| **Beacons** | Bio/link — tem modo agency/revenda | AVALIAR/REVENDER | `revenda-ferramentas` |
| **Evolution API / Baileys** | WhatsApp não-oficial | ABSORVER/AVALIAR | `mod-comunicacao-wpp`; Zernio (assess) é alt de API |
| **Chatwoot (exemplo)** | Atendimento open-source self-hosted | AVALIAR | `absorver-opensource` (exemplo, não obrigatório) |

## Infra / Deploy
| Ferramenta | Uso hoje | Decisão | Módulo/nota |
|---|---|---|---|
| **Hostgator** | Hospedagem de sites de cliente | MANTER→migrar | futuro `micro-aws-hosting` |
| **Vercel** | Deploy de PoCs (`poc.evergreen`) | MANTER | `eg-publish`, `mod-site-cms` |
| **Supabase** | (adotando) Auth+Postgres+RLS da plataforma | ABSORVER (base) | ADR-0002/0003 `mod-multitenant`; ring trial no `stack.json` |
| **Netlify / GitLab self-host** | — | AVALIAR | `hospedagem-seguranca` (privacidade/segurança) |
| **Stripe** | (futuro) pagamentos | ABSORVER | `mod-saas-billing` |

## Proveniência de skills/MCP (parte 2)
Regra: toda skill/MCP registra a **origem** (Anthropic? pesquisa? doc oficial? repo?). Fonte viva dos MCPs ativos = `.mcp.json` + `_opensquad/skills/`. Ideia dedicada: `proveniencia-skills-mcp`.

> Manutenção: atualizar quando assinar/cancelar ferramenta ou quando um ADR decidir absorver/revender. Não duplicar aqui o Tech Radar (`stack.json`) nem os princípios (`arquitetura.md`).
