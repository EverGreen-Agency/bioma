# Stack e Runtime do Bioma — documento de decisão

- **Status:** proposta ao Juiz (Eduardo) — Fase E do backlog só inicia após o aceite daqui
- **Data:** 2026-07-08 · **Autor:** Fable 5 (sessão de engenharia)
- **Relação:** consolida e defende ADR-0001 (stack), ADR-0002 (auth), ADR-0003 (RLS), ADR-0004 (região), ADR-0007 (filas). Não substitui os ADRs; responde às perguntas levantadas em 2026-07-08.

## 1. Mapa de runtime — o que roda ONDE (hoje, no código real)

| Camada | Onde roda | O que faz | Evidência no repo |
|---|---|---|---|
| **Browser** | máquina do usuário | SÓ interação: forms, toggles, kanban drag futuro. **Zero lógica de negócio, zero segredo, zero query.** | ~9 arquivos `"use client"` (`login-form`, `credential-row`, `org-switcher`, `theme-toggle`…) |
| **Servidor Next** | Vercel (funções serverless, região gru1) — ou Railway se preferir contêiner | React Server Components (renderização + leitura via RLS) e Server Actions (Zod → authz → mutação → audit). **Toda autorização acontece aqui + no banco.** | `src/app/**/page.tsx` (RSC), `src/server/actions/*` |
| **Worker** | Railway/Fly (processo Node persistente) — **NUNCA Vercel** | Jobs BullMQ: ingestão de BI, e-mails, sync, futuros squads IA. Retries + DLQ→incidente. | `src/server/queue/worker.ts` (`npm run worker`) |
| **Postgres + Auth + Storage** | Supabase região São Paulo (sa-east-1) | Dados com **RLS forçada** (isolamento é do banco, não da aplicação), identidade/sessão (GoTrue), arquivos privados. | `supabase/migrations/*` (fonte canônica) |
| **Redis** | Upstash (ou Railway Redis) | Fila do BullMQ. Nada além de fila (sem cache de dado sensível). | `src/server/queue/index.ts` |

**Resposta direta à pergunta "está tudo no frontend? A Vercel aguenta?":** não está no frontend. O que parece "frontend" (páginas React) executa no **servidor** — o browser recebe HTML pronto. A Vercel aguenta exatamente a parte que ela foi feita para aguentar (request/response curto); o que ela NÃO aguenta já está separado por arquitetura (worker).

## 2. Vercel — o que cabe e o que não cabe

**Cabe:** SSR/RSC, server actions (<30s), ISR/cache de página, API routes leves (health, webhooks que só enfileiram). Escala horizontal automática por request; frio ~centenas de ms.
**NÃO cabe (e já está fora):** worker persistente (BullMQ exige processo vivo), jobs longos (ingestão de Ads, geração de relatório), WebSockets próprios, cron pesado. → Railway/Fly, deploy do MESMO repositório (`npm run worker`).
**Regra da casa (ADR-0007):** rota Next nunca espera job — enfileira e devolve 202. Isso é o que impede a plataforma de "cair porque a Vercel tem timeout".

## 3. Matriz de alternativas (tradeoffs reais)

### 3.1 Next full-stack vs frontend Vercel + backend separado (Express/Nest/FastAPI no Railway)
| Critério | Next full-stack (atual) | Front + backend separado |
|---|---|---|
| Segurança | 1 superfície de auth; sessão via cookie httpOnly; RLS no banco | 2 superfícies (CORS, tokens entre front/back); RLS igual possível |
| Velocidade c/ IA (1 dev) | **Alta**: 1 repo, 1 tipo, feature ponta-a-ponta num arquivo de action | Média: contrato duplicado (types/DTO), 2 deploys, 2 pipelines |
| Manutenção | 1 framework para aprender/atualizar | 2 stacks envelhecendo separadas |
| Escala | Serverless escala leitura; gargalo real é o BANCO, igual nos dois | Backend dimensionável fino (útil em CPU-bound — não é nosso caso) |
| Lock-in | Baixo-médio (Next roda em qualquer Node/contêiner — inclusive Railway) | Baixo |
| Quando o separado ganha | — | Time com devs backend dedicados; APIs públicas grandes; CPU-bound pesado |

**Recomendação:** manter Next full-stack. **Importante:** isso NÃO casa com a Vercel — o mesmo app Next roda em contêiner no Railway se um dia preferirmos (é a saída de emergência do serverless). O worker já vive fora de qualquer forma.

### 3.2 Supabase vs Postgres gerenciado puro (RDS/Neon/Railway PG)
| Critério | Supabase | Postgres puro |
|---|---|---|
| O que entrega | Postgres + Auth + Storage + pooler + PITR num pacote, região BR | Só o banco; auth/storage/pooler você monta |
| Custo MVP | Free→$25/mês (Pro) | Similar no banco, MAS + auth (Clerk $) ou + build próprio (risco) |
| Lock-in | **Menor do que parece**: o schema `public` inteiro é Postgres puro (ver §4.5) | Zero por definição |
| Risco | Empresa intermediária entre nós e o Postgres | Mais peças = mais integração manual |

**Recomendação:** Supabase enquanto valer; a fronteira de saída está desenhada (§4.5).

### 3.3 Auth: Supabase Auth vs Auth.js vs Clerk vs Keycloak
- **Supabase Auth (atual):** identidade+sessão prontas, JWT integra nativo com RLS, dados de auth NO BRASIL junto do banco. Contra: RBAC hierárquico é nosso (já construímos — memberships/roles no schema).
- **Auth.js:** biblioteca, não plataforma — reintroduz "montar auth na mão" (reset, e-mail, sessão) = o anti-padrão que o Juiz vetou no ADR-0002.
- **Clerk:** melhor DX de orgs, mas PII de auth nos EUA + custo por MAU + vendor a mais. Ganha se cliente enterprise exigir SSO/SAML amanhã.
- **Keycloak:** self-host poderoso e pesado; faz sentido no cenário micro-AWS/self-host (P14), não agora.
**Recomendação:** manter Supabase Auth. Gatilho de troca: exigência enterprise de SSO federado → Clerk/WorkOS **sem refazer o modelo** (orgs/RBAC são nossos, só troca o emissor de identidade).

### 3.4 ORM: Drizzle vs Prisma vs SQL puro
- **Drizzle (atual):** tipos sem codegen pesado, SQL-like (a IA erra menos), leve p/ serverless. Uso real: espelho de leitura tipada; **DDL+RLS ficam em SQL puro nas migrations** (fonte canônica) — o melhor dos dois.
- **Prisma:** DX boa, mas engine própria, cold-start maior, migrations opinativas que brigam com RLS/policies manuais.
- **SQL puro só:** máximo controle, zero tipo — caro de manter com IA gerando código.
**Recomendação:** manter Drizzle + SQL canônico. Custo de troca: baixo (queries são finas; RLS não depende do ORM).

### 3.5 Filas: BullMQ/Redis vs SQS vs QStash vs pg-boss
- **BullMQ (atual):** maduro, retries/DLQ/concorrência prontos, mesmo TypeScript/regras do app. Contra: exige Redis + processo persistente.
- **pg-boss:** fila NO Postgres (menos uma peça!) — alternativa séria se quisermos cortar o Redis no MVP; menos throughput/recursos.
- **SQS/QStash:** gerenciadas, mas acoplam à AWS/Upstash HTTP e fragmentam o modelo (regra nº1 do Eduardo: não fragmentar).
**Recomendação:** manter BullMQ. **Gatilho de simplificação:** se até a Fase 1 nenhum job de verdade existir, trocar por pg-boss e cortar o Redis é mudança de 1 arquivo (`queue/index.ts` é o único ponto de contato).

## 4. Defesa técnica do Supabase (as 6 provas pedidas)

1. **Como a RLS é testada:** suíte real contra o Postgres local (34+ testes em `bioma/tests/rls/`) simulando usuários com `set local role authenticated` + claims — o MESMO mecanismo do PostgREST em produção. Cobrem: IDOR por id direto, INSERT/UPDATE/DELETE cross-tenant, papéis (CA2), white-label (cliente-da-agência não vê a agência), audit append-only, suspensão com herança. Roda em todo `npm test`; entra em CI no deploy.
2. **Como evitamos vazamento cross-tenant:** (a) RLS **FORCE** em toda tabela — nem o dono da tabela escapa; (b) funções `app.*` SECURITY DEFINER com search_path fixado decidem o escopo (`accessible_org_ids`), nunca a aplicação; (c) 2ª linha: toda action valida `requirePermission(recurso)` antes do banco; (d) service-role só em `admin.ts` server-only, cada uso justificado + auditado; (e) teste novo obrigatório por tabela nova (padrão `notes`).
3. **Backup/restore:** plano Pro = backup diário + PITR. Independente disso, job semanal no worker roda `pg_dump` → storage privado criptografado (não dependemos só do vendor). Restore ensaiado = `psql < dump` em qualquer Postgres.
4. **Limites de escala e mitigação:** conexões (serverless multiplica) → Supavisor pooler já incluso (transaction mode); nossa meta de 1º ano (dezenas de tenants, centenas de usuários — spec §RNF) fica ordens de magnitude abaixo do teto do plano Pro; auth rate-limits configuráveis; o gargalo real futuro é ingestão de BI → resolve no worker + snapshots, não no Supabase.
5. **Plano de saída (o mais importante):** o que é **Postgres portável** = TODO o schema `public` (tabelas, RLS, funções `app.*`, triggers) + Drizzle + SQL — migra via `pg_dump` para RDS/Neon/self-host **sem reescrever**. O que é **Supabase-specific** = GoTrue (schema `auth.*` + `@supabase/ssr` nos 4 arquivos de `src/lib/supabase/`), Storage e Realtime (ainda nem usamos). Troca de auth = trocar o emissor de JWT + a FK `profiles.id` — o RBAC/orgs continuam intactos porque são NOSSOS. Esforço estimado de saída: dias, não meses.
6. **"Supabase é para projeto pequeno?"** — o mecanismo de isolamento não é do Supabase: é **RLS do Postgres**, padrão usado por SaaS multitenant grandes há uma década. O Supabase é o empacotamento (hosting BR + auth + pooler). Se ele ficar pequeno para nós, o §5 acima é o caminho — e é por isso que NADA no domínio depende de API proprietária dele.

## 5. Riscos da stack e gatilhos de revisão

| Risco | Sinal de alerta | Resposta preparada |
|---|---|---|
| RBAC que a RLS não expressa bem | policies ilegíveis/lentas | mover regra p/ camada de serviço + testes; RLS vira "chão" mínimo |
| Timeout serverless em action | action >10s | mover para job (fila já existe) |
| Custo Supabase escalando | fatura > contrato de cliente | §4.5 exit plan |
| Next major quebrando (16→17) | breaking changes | app é contêiner-izável; segurar upgrade |
| Session-limit da IA em agentes | trabalho pela metade | ondas curtas + coordenador retoma inline (já operacional) |
| Redis/worker ocioso no MVP | zero jobs reais até Fase 1 | trocar BullMQ→pg-boss (1 arquivo) e cortar Redis |

## 6. Recomendação global

**Manter: Next full-stack (monólito modular) + Supabase BR (Postgres/RLS/Auth) + Drizzle com SQL canônico + BullMQ com worker fora da Vercel.** Não por moda — porque: (a) 1 dev + IA entrega ponta-a-ponta sem fricção de contrato entre repos; (b) o isolamento mora no Postgres (portável, testado, à prova de esquecimento); (c) cada peça tem plano de saída documentado e barato; (d) região BR para dado E auth resolve LGPD sem DPA transfronteiriço.

O que me faria mudar a recomendação: time com 2º dev backend dedicado (aí front/back separado volta ao jogo), cliente enterprise exigindo SSO federado (Clerk/WorkOS na frente do nosso RBAC), ou throughput de jobs que Redis single não dê conta (aí SQS/particionamento).
