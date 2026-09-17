# Spec: mod-multitenant (fundação da Mega Plataforma EG)

- **Cliente:** interno (`target: internal`) — ideia `mod-multitenant` (part_of `mod-nucleo` → `mega-plataforma`)
- **Autor:** Especificador EG
- **Data:** 2026-07-06
- **Status:** rascunho
- **Versão:** 1.0

> Esta spec é o **contrato** do projeto. Código e tarefas derivam dela. Mudança de escopo = nova versão da spec, não decisão de corredor.

## 1. Objetivo
Estabelecer a **fundação multi-tenant** (identidade, papéis, isolamento de dados) sobre a qual todos os módulos da mega-plataforma são construídos — evoluindo do cockpit atual — para que a EG opere internamente, depois com/para clientes, e por fim como produto white-label público.

## 2. Contexto
Hoje o cockpit (`dashboard/`, Vite+React+TS) é **local, sem autenticação**, com os bancos em **JSON versionado** e contexto de cliente por filesystem (`_opensquad/_memory/clients/<id>/`). A mega-plataforma **cresce DESTE código** (é a evolução do cockpit, não um app à parte): interno → com/para cliente → white-label. Nada disso é possível sem uma camada de **tenancy + auth + isolamento**. Este projeto é essa fundação. Decisão de negócio: multitenant é a peça que destrava client-hub, billing e o modelo de agências-parceiras (D7). **Refactor de stack/estrutura é permitido** — a escolha de *como* (manter Vite, migrar, introduzir backend/DB) é dos ADRs (Decisor Técnico); esta spec descreve o **quê** e o **porquê de negócio**.

## 3. Escopo
O que **será** construído (1º corte = só a fundação):
- **Árvore de organizações/tenants** com 4 níveis já no schema: **EG** (super-admin/plataforma) → **cliente** (tenant) → **agência-parceira** (reseller tenant) → **cliente-da-agência** (sub-tenant). Cada org tem `tipo` e `parent_id`.
- **Autenticação** (login + sessão segura) e **OAuth** para contas externas (tokens criptografados) — padrão do blueprint (`oauth_accounts`).
- **Usuários** e vínculo **usuário↔org com papel**; **RBAC** (papéis/permissões) por tipo de usuário (super-admin EG, admin de tenant, operador, cliente-visualizador).
- **Isolamento de dados por tenant**: toda entidade de produto carrega `tenant_id`; leitura/escrita sempre filtrada por tenant, com mecanismo forte (RLS ou equivalente — ADR).
- **Superfície mínima autenticada**: login → landing do próprio tenant (nome/contexto + placeholder de onde os módulos futuros — client-hub etc. — vão morar).
- **Camada de dados de produto** (tenant/usuário/cliente/oauth/audit) em **banco relacional** (blueprint usa PostgreSQL), **distinta** dos bancos internos JSON (ideias/stack/arquitetura), que permanecem git-versionados (D2).
- **Audit log** de ações sensíveis e de auth (`audit_logs`).
- **Continuidade a partir do código atual**: o cockpit interno segue funcionando (preservado ou migrado) — a plataforma nasce como sua evolução, não substituição abrupta.
- **Super-admin EG** cria/edita/**suspende** tenants e usuários (suspensão = base da retenção legítima).

## 4. Fora de Escopo
O que explicitamente **não** entra neste 1º corte:
- **UI de gestão da agência-parceira** (reseller) — o schema suporta; a tela vem depois.
- **Billing/pagamentos/planos/cotas** (Stripe) — é `mod-saas-billing`, fase seguinte.
- **client-hub, BI, financeiro, RH e demais módulos** — constroem-se EM CIMA desta fundação, não aqui.
- **Migração dos bancos internos JSON → DB** — é `banks-portability`, decisão futura (D2 se mantém p/ eles).
- **SSO federado** (Google/Microsoft Workspace) além do login próprio. `[SUPOSIÇÃO: fora do 1º corte — confirmar]`
- **Mobile nativo**; onboarding automatizado de tenant (é `mod-comercial`).

## 5. Requisitos Funcionais
- **RF1** — Usuário faz login por credencial segura e recebe sessão isolada; sessão expira.
- **RF2** — Sistema modela orgs em árvore (EG → cliente → agência-parceira → cliente-da-agência) com `parent_id` e `tipo`; aceita os 4 níveis já no MVP.
- **RF3** — Usuário pertence a uma ou mais orgs, cada vínculo com um papel definido.
- **RF4** — RBAC controla leitura/escrita por papel: super-admin EG vê a plataforma; admin de tenant vê só o próprio tenant (e descendentes conforme regra); operador e cliente-visualizador têm escopos restritos.
- **RF5** — Toda entidade de produto carrega `tenant_id`; nenhuma rota/consulta retorna dado de outro tenant.
- **RF6** — Contas externas (OAuth) conectadas **por tenant**; tokens criptografados, nunca em `.env` global (generaliza o princípio de isolamento `client_id` → `tenant_id`).
- **RF7** — Ações sensíveis (login, CRUD de org/usuário, conexão de conta, mudança de papel, suspensão) geram entrada em `audit_logs`.
- **RF8** — Usuário autenticado vê a superfície mínima do próprio tenant (contexto + placeholder de módulos).
- **RF9** — Super-admin EG cria/edita/**suspende** tenants e usuários; suspensão **bloqueia o acesso** (retenção legítima — nunca backdoor de travamento).

## 6. Requisitos Não-Funcionais
- **Segurança / dados:** isolamento por `tenant_id` com mecanismo forte (RLS ou equivalente — ADR); tokens OAuth criptografados; acesso admin/financeiro restrito por papel; **sem PII em logs**. O teste de IDOR (acessar `/recurso/{id}` de outro tenant) deve **falhar**.
- **LGPD / residência:** dados sensíveis e backend em **região BR** (Vercel/Railway têm região BR; *managed ≠ dado fora do BR* — correção do ADR-0005/rian-pje). Finalidade, necessidade, controle de acesso e trilha de auditoria.
- **Performance:** auth e leitura de contexto do tenant **< 300ms p95** (alvo).
- **Escala:** `[SUPOSIÇÃO: dezenas de tenants e centenas de usuários no 1º ano; arquitetura não deve impedir milhares depois — confirmar ordem de grandeza]`.
- **Continuidade / operação:** evolui do código atual; HTTPS em produção; rotina de backup do banco de produto.
- **Manutenibilidade:** modular — cada módulo futuro pluga sobre esta fundação; decisões de stack registradas em ADR.

## 7. Critérios de Aceite
- **CA1** — Dois tenants com dados: usuário do tenant A **não** consegue, por nenhuma rota/ID, ler/escrever dado do tenant B (teste de isolamento passa; IDOR falha).
- **CA2** — Papéis aplicados: operador não acessa o de admin; super-admin EG lista tenants; admin de tenant vê só o seu.
- **CA3** — Login seguro funciona; sessão expira; token OAuth persistido **criptografado** (dump do banco não vaza token em claro).
- **CA4** — Árvore de orgs com os 4 níveis existe no schema e aceita um cliente-da-agência sob uma agência-parceira sob a EG (mesmo sem UI de reseller).
- **CA5** — Ações sensíveis aparecem no `audit_logs`.
- **CA6** — Super-admin suspende um tenant e o acesso é bloqueado imediatamente.
- **CA7** — App publicado em ambiente web (dados em região BR), HTTPS. *(Revisado 2026-07-07: o cockpit atual (`dashboard/`) não tem uso operacional real — sem auth, sem operação de negócio passando por ele, é só visualizador local de bancos/ideias. Não é uma premissa a proteger. CA7 vira só "publicar corretamente"; ver §9 sobre a estratégia de migração.)*

## 8. Riscos e Dependências
- **Risco:** escolha de auth (build vs buy) e do mecanismo de isolamento (RLS) define custo/segurança → **Mitigação:** ADRs dedicados antes de codar.
- **Risco:** evoluir do código atual (Vite / JSON / sem-auth) pode exigir refactor grande (introduzir DB + backend + auth) → **Mitigação:** ADR de arquitetura decide *keep-vs-migrate*; MVP fino reduz a superfície.
- **Risco:** misturar bancos internos (JSON) com dados de produto (DB) → **Mitigação:** fronteira explícita — bancos internos em arquivo (D2), dados de tenant no DB.
- **Dependência:** provedor de auth e de banco (a decidir em ADR) + região BR de hosting → **Necessário até:** antes do scaffold.
- **Dependência:** stack de produto (Postgres, framework web/backend) precisa **entrar no `stack.json`** (o radar hoje não cobre) → Decisor registra.

## 9. Nota de revisão — cockpit sem uso operacional (2026-07-07)
O Eduardo confirmou: **o cockpit atual (`dashboard/`) não é operável** — sem login, sem operação de negócio (não roda cliente, não roda financeiro, não roda nada crítico), é um visualizador local dos bancos internos (ideias, arquitetura, stack). Isso muda a estratégia de migração do ADR-0001: **não há necessidade de "strangler para preservar"** — a plataforma nova (Bioma) pode ser construída **greenfield**, e as poucas telas úteis do cockpit (Banco de Ideias, Tech Radar) são **portadas por valor, não por obrigação de compatibilidade**. Ver ADR-0001 §4 atualizado.

---
<!-- [SUPOSIÇÃO] pendentes: (1) SSO federado fora do 1º corte; (2) ordem de grandeza de escala; (3) bancos internos JSON permanecem em arquivo (D2). Confirmar no gate de aprovação. -->
