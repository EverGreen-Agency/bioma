# Mega Plataforma EG

**Id:** `mega-plataforma` · **Categoria:** Platform · **Stage:** project · **Horizonte:** NOW

## O que é
O **sistema operacional da EG** — modular e multi-tenant — que unifica método, dados, squads, bancos de conhecimento, entregáveis, governança e a experiência do cliente numa infra só. Não é uma ferramenta; é a **infraestrutura que roda a agência e depois vira produto**. Já engloba o que foi construído (cockpit, bancos, squads, entrega, RAG) e a superfície de negócio a construir (client-hub, financeiro, RH, billing, site/CMS, comunicação).

## Posicionamento (o que ela NÃO muda)
A EG continua **boutique premium** — seletiva, método visível, alta inteligência aplicada. A boutique **nunca foi nichada por mercado**: atende qualquer setor com potencial real de crescimento; **solar é um ICP prioritário momentâneo/documentado**, não uma limitação estrutural. A plataforma **não** empurra a EG para "agência 360" — ela é o **moat** (diferencial técnico), não uma diluição do posicionamento.

## O moat — prende pelo valor, não por trava
O cliente fica porque **sair dói operacionalmente** (perde BI, score, histórico, relatórios, comunicação, automações integradas), não por aprisionamento técnico abusivo. Mesma lógica de ecossistema Apple/Android. Reforça o pilar **Conversão** da metodologia e permite cobrar o CRM/plataforma à parte.

## Regra de ouro — cada módulo evolui em 3 fases
Todo módulo é um **bloco de Lego que atravessa 3 fases sem reescrever** (por isso multi-tenant e modularidade são fundação, não enfeite):
1. **Interno/operacional (EG):** a EG usa pra si primeiro (dogfooding). Ex.: financeiro nasce da planilha pessoal → corporativo.
2. **Com/para o cliente:** superfície que a EG opera *para* o cliente e o cliente *consome* (client-hub, BI, score, relatórios; módulos desbloqueáveis por oferta contratada).
3. **Produto / white-label (SaaS):** empacota para outras agências/consultorias e os clientes delas (billing, planos, cotas). Modelo "Service-as-Software" (referência Kelvin Cleto).

## Objetivos
- **Controle** da EG sobre execução, dados, qualidade e previsibilidade.
- **Retenção/moat:** cliente pode sair da consultoria e ainda querer pagar o sistema.
- **Percepção premium:** portal, BI, score, relatórios, artefatos e kits integrados.
- **Margem/escala:** IA no backoffice, humano no julgamento — boutique premium sem depender de volume de gente.
- **Ecossistema (flywheel):** funcionário, cliente e futuro investidor com vantagem crescente por pertencer (holding Quark no horizonte).

## Módulos (`part_of: mega-plataforma`)
Núcleo (`mod-nucleo` → multitenant/SSO/permissões, blocos Lego, LLM-agnostic) · Cockpit interno (`mod-cockpit-interno`, ~construído) · Comercial (`mod-comercial`) · Entrega mkt (`mod-entrega-mkt`) · Conhecimento (`mod-conhecimento`, + vídeo YT/Insta) · Radar/Pesquisa (`mod-radar-pesquisa`, + `squad-negocios`, + `mod-policy-research`) · Marca/Artefatos (`mod-marca-artefatos`) · **Área do Cliente** (`client-hub`, + `mod-bi-dashboards`) · Financeiro (`mod-financeiro`) · RH (`mod-rh`, + certificações) · Logística de kits (`mod-logistica-kits`) · Contratos/Autentique (`mod-contratos`) · Billing/SaaS (`mod-saas-billing`) · Site/CMS/EG Lab (`mod-site-cms`) · WhatsApp/omnichannel (`mod-comunicacao-wpp`).

## Fronteiras (SEPARAR — umbrellas irmãs sob a Quark)
`foton` (pessoal do Eduardo), `prisma-bi`, `telecom-chips`, `micro-aws-hosting`, `educacao-comunidade`, `trade-autonomo`. Podem reintegrar/reusar módulos, mas **não contaminam o core no 1º ciclo**.

## Blueprint de referência já existente
A proposta **HM Conexões** (`Proposta_..._v3.pdf`) é um **protótipo single-tenant** do que a plataforma generaliza: modelo de dados (`users, oauth_accounts, clients, leads, briefings, ai_artifacts, content_items, integrations, ad_accounts, ad_campaigns, metric_snapshots, reports, contracts, financial_entries, audit_logs`), arquitetura monólito-modular (Next.js + PostgreSQL fonte-da-verdade + Redis/Celery workers + LLM com JSON Schema) e premissas de LGPD. **Reaproveitar** como base do `mod-multitenant` + `client-hub`. O **BIAds** (repo irmão) é a base do `mod-bi-dashboards`. A **planilha orçamentária pessoal** é o protótipo do `mod-financeiro` (→ nasce no Fóton).

## Sequência recomendada
`mod-multitenant` (fundação de acesso/tenancy) → `client-hub` + `mod-bi-dashboards` (o que o NFC do kit aponta e o cliente pede hoje) → resto do backoffice por dogfooding. **Regra de código:** spec (SDD) + ADR aprovados de um módulo = já pode codar aquele módulo (Fable 5, subagentes + worktrees); módulos independentes paralelizam; os dependentes esperam a fundação.

## 🚩 Guardrail
Retenção legítima = **suspensão contratual de acesso** (em `mod-saas-billing`), **NUNCA backdoor de travamento** do sistema do cliente (risco jurídico/criminal/LGPD e destrói o premium).

---
*Registrado 2026-07-06 (sessão dispatcher → Curador → Arquiteto). Decisão arquitetural correspondente: **D7** no `arquitetura.md`. Classificação completa do banco: `mega-plataforma-classificacao-EG.md` (raiz do repo).*
