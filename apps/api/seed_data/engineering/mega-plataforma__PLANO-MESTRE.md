# PLANO-MESTRE — Mega Plataforma EG
*Guia de especificação distribuída. Outras LLMs especificam módulo a módulo; o Opus (Claude) revisa no fim e preenche lacunas.*

**Data:** 2026-07-06 · **Fonte da verdade da visão:** `_opensquad/_memory/banco_ideias/docs/mega-plataforma.md` · **Decisão:** D7 no `arquitetura.md` · **Classificação:** `mega-plataforma-classificacao-EG.md` (raiz).

---

## 0. Como usar este plano
**Contexto obrigatório que QUALQUER LLM deve ler antes de especificar um módulo:**
1. `_opensquad/_memory/company.md` (quem é a EG — boutique premium, **não nichada por mercado**; solar é ICP momentâneo).
2. `_opensquad/_memory/banco_arquitetura/arquitetura.md` (princípios + decisões D1–D7).
3. `docs/mega-plataforma.md` (visão: moat, 3 fases por módulo, módulos, fronteiras).
4. O registro do módulo no `ideas.json` (+ `docs/<id>.md` se existir).
5. **O blueprint do PDF HM** (`Proposta_..._v3.pdf`): modelo de dados + arquitetura monólito-modular — reaproveitar.
6. Este plano.

**Fluxo por módulo (SDD):** Arquiteto (parecer, só se capacidade nova) → Especificador (`spec.md`) → Decisor Técnico (`ADR-NNNN`) → Scaffolder (esqueleto + `tasks.md`) → código (Fable 5). Templates em `squads/eg_engenharia/templates/`.

**Regra de liberação:** spec + ADR aprovados de um módulo = pode codar aquele módulo. Fundação primeiro; módulos independentes paralelizam.

**Papel do Opus (revisor):** apontar erro/risco/contradição e o que faltou; não refazer o que já ficou bom.

---

## 1. Decisões de PLATAFORMA (ADRs transversais — decidir 1x no `mod-multitenant`, herdar em todos)

> ⚠️ **Numeração P1–P8 abaixo está HISTÓRICA/SUPERSEDIDA (2026-07-07).** As decisões já foram tomadas e viraram ADRs de verdade em `_opensquad/_memory/engenharia/mod-multitenant/adr/ADR-0001..0010-*.md` (fonte canônica). P9–P14 (workspace/cofre/créditos-IA/revenda/self-host/nome) viraram módulos/ideias próprios — ver §6 e `roadmap-p0-p1.md`. Mantido aqui só como registro do raciocínio original; **não usar esta numeração P1–P8 em documentos novos.**

- **ADR-P1 — Stack base / keep-vs-migrate.** A plataforma evolui do cockpit atual (Vite+React+TS, backend via plugin Vite `squadWatcher`, bancos JSON, sem auth). Opções: (a) manter Vite+React e adicionar backend/API+DB; (b) **migrar p/ Next.js** (blueprint: SSR + API routes + ecossistema auth/multitenant); (c) Vite + backend separado (FastAPI/Django). Critérios: continuidade com o código atual, auth/multitenant nativos, workers, esforço de refactor. *Avaliar seriamente (b) — o blueprint aponta pra lá e o cockpit atual é pequeno; refactor é permitido (decisão do Eduardo).*
- **ADR-P2 — Auth build-vs-buy.** Avaliar **Clerk** vs **Supabase Auth** vs Auth.js/NextAuth vs WorkOS vs próprio. Critérios EXPLÍCITOS: multitenancy/organizations nativo (Clerk e WorkOS têm orgs+roles prontos), RBAC, **custo por MAU/tenant**, **residência de dados BR/LGPD** (onde o provider guarda os dados de auth?), self-host/lock-in, SSO federado futuro, DX. *Clerk = orgs+RBAC+UI prontos, DX excelente, rápido; contras: dados no exterior (checar LGPD p/ dados de auth), custo por MAU escala. Supabase Auth = casa com Postgres+RLS, self-hostável, BR-friendly. Pôr AMBOS no ADR com trade-offs numéricos.*
- **ADR-P3 — Banco + isolamento.** PostgreSQL (Supabase/Neon/RDS região BR) + **RLS** (isolamento no banco) vs isolamento app-level. RLS = padrão-ouro multi-tenant.
- **ADR-P4 — Hosting/região.** Backend + dados sensíveis em **região BR**; frontend livre. (Vercel/Railway/Fly têm BR; managed ≠ dado fora do BR.)
- **ADR-P5 — Modelo de tenancy.** Árvore de orgs (EG→cliente→agência-parceira→cliente-da-agência), `tenant_id` em toda entidade de produto, papéis por vínculo usuário↔org.
- **ADR-P6 — Fronteira de dados.** Bancos internos (ideias/stack/arquitetura) ficam em arquivo JSON/git (D2); dados de produto (tenant/cliente/oauth/métricas/financeiro) no DB. Migração JSON→DB é futura (`banks-portability`).
- **ADR-P7 — Workers/filas.** BullMQ (Node) ou Celery/RQ (Python) p/ tarefas assíncronas (IA, coleta de Ads, Notion). Do blueprint.
- **ADR-P8 — Camada LLM-agnostic.** LiteLLM/OpenRouter (`llm-agnostic`) — trocar modelo por config.

---

## 2. Sequência (fases)
- **Fase 0 — Fundação:** `mod-multitenant` *(spec FEITA; faltam ADR-P1..P8 + scaffold)*.
- **Fase 1 — O que o cliente vê:** `client-hub` + `mod-bi-dashboards` (reusa BIAds).
- **Fase 2 — Backoffice EG (dogfood):** `mod-financeiro` (do Fóton), `mod-comercial` (consolida squads existentes), `mod-contratos`, `mod-marca-artefatos`, `mod-conhecimento`.
- **Fase 3 — Monetização/escala:** `mod-saas-billing`, UI reseller (agência-parceira), `mod-site-cms`.
- **Fase 4 — Amplos:** `mod-rh`, `mod-logistica-kits`, `mod-certificacoes`, `mod-comunicacao-wpp`, `mod-conhecimento-video`, `squad-negocios`, `mod-policy-research`.
- **SEPARAR (paralelo, quando `readiness` permitir):** `foton`, `prisma-bi`, `telecom-chips`, `micro-aws-hosting`, `educacao-comunidade`, `trade-autonomo`.

---

## 3. Briefing por módulo (o que a LLM deve especificar)
> Formato: **foco da spec** · **ADRs-chave** · **depende de** · **reaproveitar**.

- **mod-multitenant** — *SPEC FEITA.* Falta: ADR-P1..P8 + scaffold. · reusar: blueprint PDF (data model + arquitetura).
- **client-hub** — foco: área do cliente (destino NFC, **score + micro-scores** [branding etc.], dashboards, relatórios, comunicação centralizada, **funil Kotler 5A / all-bound**, health/SLA, viz árvore-crescimento, **módulos desbloqueáveis por oferta**). · ADR: desbloqueio por plano/oferta; layout premium. · depende: mod-multitenant, mod-bi-dashboards. · reusar: telas do PDF (dashboard geral, cliente+briefing), `skill-raiox`, `Playbook_Metodologia`.
- **mod-bi-dashboards** — foco: motor de BI (Meta/Google/LinkedIn Ads, funil dinâmico, criativos, UTMs) interno + cliente; multi-tenant (BIs EG × cliente × funcionários-do-cliente). · ADR: **embed (Looker/Metabase) vs build (Recharts)**; coleta (CRON/webhook); OAuth por conta. · depende: mod-multitenant, `ads-api-skills`. · reusar: **repo BIAds**, `abstracao-bi.md` (3 dashboards), `meta_ads_dashboard_prompt.md`.
- **mod-financeiro** — foco: viabilidade/forecasting/metas + cobrança + contábil/fiscal (NF, situação cadastral). · ADR: integração bancária/contábil (build vs Conta Azul/etc.). · depende: mod-multitenant. · reusar: **a planilha pessoal** (modelo Metas&Projetos + orçamento 70/10/20) — **nasce no Fóton**, generaliza p/ EG. Refs: Pierre, Mobills.
- **mod-comercial** — foco: consolidar squads (prospector/proposals/onboarding/reuniões) + carteira + funil + lead scoring numa superfície multi-tenant. · ADR: CRM próprio vs Kommo (revender?). · depende: mod-multitenant. · reusar: squads existentes, `matriz-risco-comercial`, PDF (CRM/funil Kanban).
- **mod-contratos** — foco: absorver **Autentique** (ciclo/assinatura/status), ligado a financeiro/onboarding. · ADR: absorver vs manter Autentique externo (API). · depende: mod-multitenant, mod-financeiro.
- **mod-marca-artefatos** — foco: `skill-brand-eg` + `filosofia-visual-eg` + `doc-generator-eg` + `web-artifacts-builder` + `eg-publish` como camada de saída branded. · reusar: `documentacao-referencia-tecnica.md` (UI cinematográfica), `EG_Producao_de_Kits` (identidade).
- **mod-conhecimento** — foco: RAG/vector store/decay/Zep + voz do cliente + cases sucesso/fracasso + **curadoria** (não "conhecimento infinito"). · ADR: pgvector vs dedicado; política de curadoria. · reusar: `vector-store`, `segundo-cerebro`.
- **mod-saas-billing** — foco: Stripe, planos, cupons, cotas, clientes legado, white-label, **suspensão de acesso** (retenção legítima, NUNCA backdoor). · ADR: Stripe vs alternativa; modelo de planos/cotas. · depende: mod-multitenant.
- **mod-site-cms** — foco: refatoração do site EG (cases ligados ao backoffice, EG Lab/POCs, mapa de clientes, EverGreen≠Evergreen) + CMS próprio (WP/Framer/próprio). · ADR: CMS build vs buy. · reusar: `auditoriaevergreenseogeo.md`, `eg-publish`.
- **mod-comunicacao-wpp** — foco: omnichannel WhatsApp (coexistence/Evolution/VoIP + gestão de chips/números). · ADR: oficial vs não-oficial; risco de ban. · reusar: `Gemini-analise-kelvin-cleto.md` (Evolution API).
- **mod-rh / mod-logistica-kits / mod-certificacoes / mod-conhecimento-video / squad-negocios / mod-policy-research** — specs conforme `docs`/`ideas.json`; menor prioridade (Fase 4).

---

## 4. Lacunas de cobertura (áudios possivelmente perdidos — DECIDIR com Eduardo antes de virar ideia)
Comentados no doc original mas **ausentes do banco**:
1. **App mobile** — novo (`mod-mobile`?).
2. **Revenda/hospedagem de ferramentas** (ManyChat, Kommo como fonte de renda) — novo ou parte de `mod-saas-billing`.
3. **Braço BPO / EG-OS** (continuar ou aposentar? está no site) — **decisão**, não módulo.
4. **M&A / compra-e-venda de negócios / planejamento de futuras empresas** — área de backoffice (parte de `squad-negocios`/`mod-financeiro`?).
5. **Selo de qualidade / benchmark EG** (pequenas vitórias, selos bronze/prata/ouro) — só parcial (`dossie-provas`); liga ao `prisma-bi`.
6. **Estrutura de time comercial / teste de ICP** (times controle vs teste) — novo (parte de `mod-rh`/`mod-comercial`).
7. **Clonagem de personas/mentores** como feature — só solto em `educacao-comunidade`.
Menores (métodos/refs): ICE score no banco de ideias · Funnelytics/ClickFunnels · validação de API via Postman (DoD do squad de buscas).

---

## 5. Convenção de artefatos (PROPOSTA) + fix de navegação
**Problema:** hoje há 3 convenções (eng-cliente em `squads/eg_engenharia/output/<ts>/`, eng-interno em `_opensquad/_memory/engenharia/<id>/`, parecer-arquiteto achatado em `squads/eg_arquiteto/output/`). Navegar pastas dói.

**Proposta de convenção única (interno):** tudo de um módulo em `_opensquad/_memory/engenharia/<id>/`:
```
<id>/
  parecer-arquiteto.md   (se houve auditoria)
  spec.md
  adr/ADR-0001-*.md
  tasks.md
  state.json             (status: rascunho/aprovada/em-execução/entregue)
```
**Fix de navegação de verdade:** aba **"Engenharia"** no dashboard (parte de `mod-cockpit-interno`) que lê esse filesystem e renderiza, por módulo, parecer+spec+ADRs+tarefas — como o Banco de Ideias já faz. Enquanto não existe, este `PLANO-MESTRE.md` é o índice.

---
*Próximo: Eduardo distribui a especificação dos módulos entre as LLMs usando este plano; Opus revisa tudo no fim e preenche lacunas.*

---

## 6. ATUALIZAÇÃO — parte 2 + revisão do Juiz (2026-07-07)

**Docs-fonte moveram-se** de `raiz/` → `_opensquad/_memory/knowledge/inputs-mega-plataforma/` (Mega-Plataforma-parte-1/2, PDF HM, abstracao-bi, auditoria, análises, classificação; pareceres de LLMs em `pareceres-llms/`). Atualizar caminhos ao citar.

**Veredito do Juiz sobre a 1ª rodada de ADRs (0001–0008, outras LLMs):**
- Bons e mantidos: 0003 (RLS), 0004 (região BR), 0005 (tenancy — o melhor), 0006 (fronteira JSON×DB), 0007 (BullMQ), 0008 (LLM-agnostic; não construir no MVP).
- 0001 (stack Next.js+Drizzle) — adicionada **estratégia de migração strangler** (não big-bang; preservar cockpit — CA7).
- **0002 (auth) — REFEITO:** decisão = **Supabase (Auth+Postgres+RLS, região BR)**. Descartado "auth próprio" (anti-padrão de segurança) e Clerk (auth nos EUA + vendor extra). Reconciliado com 0003.
- Specs `client-hub` e `mod-bi-dashboards` = **rascunho Fase-1** (chegaram cedo; dependem da fundação). Corrigir `target` (`external/mixed` → `internal`/`platform`).

**ADRs transversais ADICIONAIS a decidir (da parte 2):**
- **P9 — Provider de auth:** ✅ resolvido = Supabase (ADR-0002 v2).
- **P10 — Workspace/e-mail próprio** (`mod-workspace`): substituir Titan/Google Workspace? **Possível overreach** — Avaliador de Negócios pesa ROI×complexidade antes.
- **P11 — Cofre de senhas/segredos** (`cofre-senhas`): vault p/ acessos de cliente/funcionário; captura Google/MCC/Meta BM no onboarding.
- **P12 — Medição de créditos de IA** (`ai-credits-metering`): uso por escopo/modelo/via (API/CLI/subscription); clientes trazem crédito. Liga ADR-0008 (`llm_runs`).
- **P13 — Profundidade de revenda** (`reseller-revenda-depth`): limite do loop agência→agência (estende ADR-0005).
- **P14 — Hospedagem/segurança self-host** (`hospedagem-seguranca`): Netlify/GitLab self-host p/ privacidade.
- **Nome da plataforma** (`nome-plataforma`): default sugerido = **Bioma**.

**Novos módulos/ideias no briefing** (specs futuras, ver `ideas.json`): `mod-juridico` (validação contrato×lei; liga `mod-contratos`) · `mod-workspace` · `mod-mobile` · `copilot-vendas` (part_of `mod-comercial`) · `ai-credits-metering` (part_of `mod-financeiro`) · `cofre-senhas` · `drive-rag-cliente` (RAG na área do cliente) · `kommo-squad-dedup` · `centralizacao-comunicacoes` · `integ-google-meu-negocio` · `revenda-ferramentas` · `absorver-opensource` · `proveniencia-skills-mcp` · `portfolio-sites-recursos` · `selo-benchmark` · `times-comerciais-ab` · `clonagem-personas` · `planejamento-negocios` · `escritorio-virtual` (baixa prioridade) · `jogo-interno` (→ Fóton/empresa de jogos, especulativo).

**Inventário de ferramentas externas** criado em `_opensquad/_memory/banco_arquitetura/ferramentas-externas.md` (Autentique, Kommo, ClickUp, Titan, Meta BM, Google Ads, Evolution, Supabase, Stripe-futuro…) com decisão por ferramenta (manter/absorver/revender/avaliar).

**Convenção de artefatos** refinada em `_opensquad/core/OUTPUT-CONVENTION.md`: run de squad × projeto de cliente/lead (área do cliente, caso Rian) × módulo de plataforma (`engenharia/<id>/`). Fix real = aba "Engenharia" no dashboard.
