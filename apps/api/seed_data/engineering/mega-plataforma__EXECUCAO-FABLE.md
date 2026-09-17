# EXECUÇÃO — Bioma / Fable 5 (documento único, autoridade total)

> **Como usar:** este é o documento que o Fable 5 lê para seguir do `mod-multitenant` em diante. Substitui a necessidade de ficar navegando entre `PLANO-MESTRE.md` / `roadmap-p0-p1.md` / `matriz-maturidade-modulos.md` / `adrs-fase-1-planejados.md` — eles continuam existindo como histórico/detalhe, mas este arquivo é o ponto de entrada.
>
> **Mandato do Eduardo (2026-07-07): entregar o backlog INTEIRO com o máximo de detalhe, sem eu (Juiz) pré-cortar escopo. O Fable é tratado como engenheiro sênior autônomo — trabalha muito, lê a documentação completa e usa o próprio julgamento sobre profundidade e sequência dentro de cada módulo.** As specs abaixo estão na versão completa (não resumida). O que eu (revisão de 2026-07-07) sinalizei como "considerar fatia mínima" é **contexto consultivo, não corte imposto** — ver §3.

---

## 1. Onde estamos

`mod-multitenant` está em produção real dentro de `bioma/` — schema com RLS forçada, funções `SECURITY DEFINER`, testes de isolamento (CA1/CA2/CA4/CA5/CA6), crypto AES-256-GCM testada (CA3), auth/authz/audit implementados. Revisão de código (2026-07-07): **sem cilada técnica, qualidade alta**. Itens que o Fable deve autoconferir antes de considerar P0 fechado (não verificados na última revisão por escopo/tempo):
- `src/server/actions/{auth,members,notes,orgs}.ts` seguem o contrato do `BUILD-BRIEF.md` (`zod.parse` + `requireUser()`/`requirePermission()` + `audit()` em toda ação sensível)?
- `src/server/queue/worker.ts` respeita `{tenantId, correlationId}` e não usa client com privilégio cross-tenant?
- `login/page.tsx` e `admin/page.tsx` são funcionais (não só scaffold default do `create-next-app`)?
- `npm run build` e `npm test` passam localmente?

Se sim → **P0 fechado**, seguir para P0.5.

**ATUALIZAÇÃO 2026-07-08 (Fable):** os 4 autochecks acima foram feitos — **P0 FECHADO** (53 testes CA1-CA7, build ok, login/admin E2E no browser). Além disso: `cofre-senhas`, `mod-observabilidade` e `mod-lgpd-governanca-dados` têm **fatia E1 em produção** (ver matriz-maturidade). UI = tema musgo do legado (default) + Viveiro operacional com banco de artefatos navegável (`/viveiro/engenharia/[id]`). Decisão de stack defendida em `STACK-RUNTIME-BIOMA.md` (**aguarda aceite do Juiz — gate da Fase E**). Próximos da fila quando liberado: `mod-integrations-hub` (migration 04) → `mod-workflows-aprovacoes` (05) → entitlements (07) → `client-hub` (08) → `mod-bi-dashboards` (09). Pendência humana: revisão jurídica LGPD; contas Sentry/BetterStack; credenciais OAuth de provedores.

## 2. Backlog completo — ordem de leitura e execução

Cada módulo: ler `spec.md` + todos os `adr/*.md` na pasta `_opensquad/_memory/engenharia/<id>/` antes de codar. Copiar o padrão da tabela `notes` (RLS por `tenant_id` + policies nomeadas) para toda tabela nova.

### P0.5 — Guardrails de fundação (fatias que o Fable dimensiona)
1. **`cofre-senhas`** — `_opensquad/_memory/engenharia/cofre-senhas/spec.md` + `adr/ADR-0001-vault-secrets.md`. Reaproveita `crypto.ts` já pronto.
2. **`mod-observabilidade`** — `_opensquad/_memory/engenharia/mod-observabilidade/spec.md` + `adr/ADR-0001-observabilidade-stack.md`.
3. **`mod-integrations-hub`** — `_opensquad/_memory/engenharia/mod-integrations-hub/spec.md` + `adr/ADR-0001-contrato-integracoes.md`. A tabela `oauth_accounts` do P0 já é a base — este módulo generaliza o padrão quando o 2º provedor aparecer.
4. **`mod-workflows-aprovacoes`** — `_opensquad/_memory/engenharia/mod-workflows-aprovacoes/spec.md` + `adr/ADR-0001-motor-aprovacoes.md`.
5. **`mod-lgpd-governanca-dados`** — `_opensquad/_memory/engenharia/mod-lgpd-governanca-dados/spec.md` + `adr/ADR-0001-governanca-dados.md`.

### P1 — Primeira camada visível
6. **`client-hub`** — `_opensquad/_memory/engenharia/client-hub/spec.md`. ADRs planejados (CH-001..CH-006) em `adrs-fase-1-planejados.md` — escrever como ADRs de verdade antes de codar cada decisão.
7. **`mod-bi-dashboards`** — `_opensquad/_memory/engenharia/mod-bi-dashboards/spec.md`. ADRs BI-001..BI-006 em `adrs-fase-1-planejados.md`. Reaproveitar repo BIAds + `abstracao-bi.md`/`meta_ads_dashboard_prompt.md` (em `knowledge/inputs-mega-plataforma/`).
8. **`mod-entrega-mkt`** — `_opensquad/_memory/engenharia/mod-entrega-mkt/spec.md`. ADRs MKT-001..MKT-004.

### P2+ — Backoffice EG e além
Ver `matriz-maturidade-modulos.md` para a lista completa (`mod-comercial`, `mod-conhecimento`, `mod-financeiro`, `mod-contratos`, `mod-marca-artefatos`, `mod-comunicacao-wpp`, `mod-saas-billing`, `mod-site-cms`, `mod-radar-pesquisa`, etc. — todos já têm spec rascunho completa em `_opensquad/_memory/engenharia/<id>/spec.md`).

### 7 gaps novos capturados nesta sessão (ainda sem spec — Especificador entra quando for a vez)
`escada-oferta-tech` (part_of `mod-comercial`) · `desvincular-opensquad` (part_of `mod-cockpit-interno` — questiona D1 do `arquitetura.md`, tratar com cuidado arquitetural) · `modulo-investimentos` (part_of `foton`) · `banco-skills-produto` (especulativo) · `squad-ativacao-por-cliente` (part_of `mod-comercial`) · `niveis-score-expandido` (part_of `client-hub`, decisão pendente do Eduardo antes de especificar) · `squad-recrutamento` (part_of `mod-rh`).

## 3. Contexto consultivo (não é gate — é para informar julgamento)

Minha revisão de 2026-07-07 observou que os 5 módulos P0.5, se implementados na profundidade total da spec (portais, checklists, motores genéricos), representam bastante superfície para uma plataforma pré-cliente. **O Eduardo decidiu explicitamente não usar isso como corte externo** — prefere entregar tudo em detalhe e deixar o próprio Fable, lendo a doutrina **N&S (Necessário e Suficiente)** do `Documento-Mestre_EG.md` §19 ("isso acelera o resultado principal? reduz esforço? cabe no escopo saudável da equipe?"), decidir quanto construir de cada vez. Use esse framework como bússola própria, não espere aprovação externa pra cada corte de escopo dentro do que já está aprovado aqui.

Único ponto que **não** é opção de julgamento, é regra dura da casa (`arquitetura.md` §1 + D7): **HITL sempre, Write/Read barrier sempre, isolamento por tenant sempre, nunca backdoor de travamento.**

## 4. Dependência circular conhecida
`mod-workflows-aprovacoes` (P0.5) ↔ `client-hub` CH-003 (P1) se referenciam mutuamente. Sugestão: `client-hub` nasce com aprovação simples e direta (hardcoded pras primeiras 2-3 ações sensíveis do cliente); o motor genérico de `mod-workflows-aprovacoes` absorve isso depois, sem quebrar o que já roda. Decisão de sequência real fica com quem estiver codando no momento.

---
*Documentos de apoio (não precisam ser lidos de novo se este arquivo já foi lido): `PLANO-MESTRE.md` (histórico + visão original), `roadmap-p0-p1.md`, `matriz-maturidade-modulos.md`, `matriz-rastreabilidade-ideias.md`, `adrs-fase-1-planejados.md`, `HANDOFF.md`.*
