# HANDOFF — Mega Plataforma EG "Bioma" (para iniciar sessões novas)

> Cole isto no começo de uma sessão nova (planejamento OU Fable 5). Atualizado: 2026-07-07.

## Estado atual (já no repo)
- **`ideas.json`: 126 ideias** — umbrella `mega-plataforma` + módulos (category **Platform**, 33 ideias) + irmãs SEPARAR + demandas da parte 1+2. Dashboard já lê `part_of`/`readiness`/category `Platform` com labels em **PT** (Plataforma/Recurso/Serviço/Comercial).
- **Visão canônica:** `banco_ideias/docs/mega-plataforma.md`. **Decisão D7** em `banco_arquitetura/arquitetura.md`.
- **Trilho:** `engenharia/mega-plataforma/PLANO-MESTRE.md` (ADRs P1–P14 + briefing por módulo + fases + §6 atualização parte 2).
- **Maturidade/execução:** `engenharia/mega-plataforma/matriz-maturidade-modulos.md`, `roadmap-p0-p1.md` e `adrs-fase-1-planejados.md`.
- **`mod-multitenant`:** `engenharia/mod-multitenant/spec.md` (APROVADA, com nota §9) + ADRs 0001–0010. Revisados pelo Juiz: 0003–0010 bons (0009 i18n, 0010 theming/white-label do Gemini, aprovados); **0001 e spec CA7 corrigidos 2026-07-07** (ver abaixo — cockpit não é operável, migração é greenfield); **0002 REFEITO → auth = Supabase**.
- **Specs adicionais:** todas as specs não-multitenant foram elevadas de briefing para rascunho estrutural completo (escopo, fora de escopo, RF, RNF, aceite, riscos). Inclui `client-hub`, `mod-bi-dashboards`, cockpit, comercial, conhecimento, financeiro, contratos, observabilidade, WPP, kits, RH, billing, site/CMS e specs futuras/transversais (`cofre-senhas`, integrações, aprovações, LGPD, entrega MKT, marca, radar, jurídico, workspace, mobile etc.). Ver `engenharia/mega-plataforma/matriz-rastreabilidade-ideias.md`.
- **Inventário de ferramentas externas:** `banco_arquitetura/ferramentas-externas.md`.
- **Convenção de artefatos:** `core/OUTPUT-CONVENTION.md` (run × cliente/lead × módulo de plataforma).
- **Docs-fonte:** `knowledge/inputs-mega-plataforma/` (parte 1/2, análises; pareceres de LLMs em `pareceres-llms/`). PDF HM removido do git (pesado; fica local, gitignorado).
- **Planilha pessoal** movida para fora do repo (`../Planilha-Orcamentaria.xlsx`) — leve pro Fóton.

## Decisões travadas
- **Nome = Bioma** (confirmado pelo Eduardo).
- **Auth = Supabase** (Auth+Postgres+RLS, região BR). **Stack:** Next.js App Router + TS + Tailwind/Shadcn + Drizzle + Postgres + pgvector + BullMQ/Redis.
- **⚠️ Migração = GREENFIELD, não strangler** (correção 2026-07-07): o cockpit atual (`dashboard/`, Vite) **não dita a plataforma nem a stack** — sem auth, sem operação de negócio real, é um visualizador local dos bancos internos. O Bioma nasce **do zero**, limpo. Ao mesmo tempo, o `/dashboard` não deve ficar largado: ele é **legado intencional**. Telas úteis (Banco de Ideias, Tech Radar, Arquitetura, Squads) serão inventariadas e portadas por valor de produto; o que não servir será descartado; quando houver equivalentes no Bioma, o Vite antigo será aposentado formalmente.
- **Isolamento = RLS por `tenant_id`.** **Tenancy:** árvore EG→cliente→agência-parceira→cliente-da-agência (+ usuário SaaS independente); orgs/RBAC/entitlements no nosso schema.
- **3 fases por módulo** (interno→cliente→white-label). **Retenção = suspensão de acesso, nunca backdoor.**
- **Workspace/e-mail próprio e jogo interno = baixa prioridade** (confirmado). LLM-agnostic (LiteLLM+PII masking) só quando features de IA entrarem.

## Sessão de PLANEJAMENTO (LLMs especificadoras; Opus é o Juiz no fim)
- Contexto obrigatório: PLANO-MESTRE + `docs/mega-plataforma.md` + `arquitetura.md` + o módulo no `ideas.json` + docs em `inputs-mega-plataforma/`. Fluxo: Especificador→Decisor→Scaffolder. **Não** especificar `client-hub`/`bi` antes da fundação.
- Fila (após multitenant): `mod-observabilidade` + `cofre-senhas` + `mod-integrations-hub`/aprovações/LGPD como apoios de fundação → `client-hub` + `mod-bi-dashboards` + `mod-entrega-mkt` (Fase 1) → backoffice (financeiro/comercial/contratos/marca/conhecimento) → billing/site → amplos. Ver `roadmap-p0-p1.md`.
- Pendências de ADR transversal: P10 workspace (baixa prioridade), P11 cofre, P12 créditos-IA, P13 revenda-depth, P14 self-host.
- **Cuidado com escrita concorrente:** se várias LLMs rodam em paralelo, apenas UMA por vez deve escrever no `ideas.json` (já aconteceu de uma reverter a category `Platform` de outra — corrigido, mas evitar repetir).

## Sessão do FABLE 5 (código)
- **Ler `engenharia/mega-plataforma/EXECUCAO-FABLE.md` primeiro** — é o documento único de execução (backlog completo P0.5+P1+P2, ordem de leitura, autoridade de julgamento). `mod-multitenant` (P0) já está em produção real dentro de `bioma/` — RLS, auth, crypto, audit testados (revisão de código 2026-07-07: sem cilada, qualidade alta). Fable segue para P0.5 com autonomia total, sem esperar corte externo de escopo — usa a doutrina N&S (`Documento-Mestre_EG.md` §19) como bússola própria.
- Segurança obrigatória (ver `inputs-mega-plataforma/documentacao-referencia-tecnica.md`): sem `.env` exposto, validação de autorização por recurso (anti-IDOR), upload sanitizado no back-end.

## Aberto p/ Eduardo
- Nenhuma pendência bloqueante — pode iniciar/continuar a sessão do Fable 5 (P0.5+) usando `EXECUCAO-FABLE.md`.
- **2ª varredura da parte 1+2 (2026-07-07):** achou +7 gaps, já capturados no banco (148 ideias): escada de oferta de tecnologia (Kelvin), desvincular do Opensquad, módulo de investimentos pessoal, banco de skills como produto, ativação de squad por cliente, expansão dos pilares de score (Lázaro Ramos), squad de recrutamento. Nenhum tem spec ainda — entram na fila quando chegar a vez.
