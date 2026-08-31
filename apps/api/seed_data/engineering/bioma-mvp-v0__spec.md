# Spec: bioma-mvp-v0

- **Cliente:** EverGreen + primeiros clientes EG
- **Autor:** Codex, com aprovação Eduardo
- **Data:** 2026-07-09
- **Status:** rascunho aprovado para planejamento
- **Versão:** 0.2
- **Ideias relacionadas:** `mega-plataforma`, `bioma-mvp-v0`, `mod-cockpit-interno`, `client-hub`, `clients-clickup-sync`, `mod-integrations-hub`, `mod-workflows-aprovacoes`, `cofre-senhas`, `mod-bi-dashboards`

## 1. Decisão de Recorte

O Bioma MVP v0 reinicia a Mega Plataforma com escopo mínimo, útil e entregável rápido.

O trabalho anterior em `bioma-legacy/` fica preservado como referência, mas não dita a arquitetura, stack, UX ou priorização. Specs antigas continuam como insumo, não como contrato do MVP.

O MVP nasce para uso interno da EG e como hub simples para clientes. White-label, SaaS público, reseller, escritório pixel art, billing completo, workspace próprio e automações avançadas ficam fora do v0.

## 2. Objetivo

Construir uma plataforma operacional mínima que:

- centralize a visão interna da EG sobre clientes, entregáveis, documentos, ideias, stack e engenharia;
- conecte ClickUp com uma camada própria de produto, sem tentar substituir o ClickUp no v0;
- entregue um Client Hub simples, inspirado no fluxo HM Conexões: dashboard, briefing, brand book/calendário, relatórios e aprovações;
- permita login por e-mail e senha para EG admin e cliente;
- deixe preparada a evolução para IA, workers, BI real, cofre seguro, NFC e white-label sem carregar esses custos no primeiro corte.

## 3. Premissas Aprovadas

- EG não é nichada por mercado. Solar é ICP documentado/momentâneo, não limitação estrutural.
- A boutique continua premium e especializada em crescimento, tecnologia, dados e operação. A plataforma cria moat; não transforma a EG em agência 360.
- Perfis v0: `eg_admin` e `client_user`. No dia a dia inicial, EG admin cobre Eduardo e CTO.
- Login inicial: e-mail e senha. Google/Microsoft/NFC/magic link entram depois, sem excluir login tradicional.
- ClickUp é ferramenta operacional de PM. Bioma é plano de controle, vitrine executiva e ponte bidirecional.
- Workers entram apenas quando houver tarefa recorrente, demorada ou sensível: sincronização ClickUp, relatório, IA, webhook ou retry.
- Backend separado do frontend é a direção preferida para o MVP, porque integra ClickUp, jobs, auditoria, segredos e IA sem acoplar tudo ao servidor do front.
- O branding visual padrão do Bioma é o da EverGreen. Mockups HM servem como referência funcional e de layout, não como identidade visual base do produto EG.

## 4. Personas

- **EG Admin:** Eduardo/CTO. Vê clientes, integra ClickUp, edita bancos, aprova ações, consulta engenharia, publica relatórios e opera o hub.
- **Cliente:** decisor ou responsável autorizado. Vê apenas seu espaço, documentos, relatórios, status, aprovações e próximas ações.

Fora do v0: gestor de projeto dedicado, social media, financeiro, admin de agência parceira, cliente-da-agência, suporte e assinante SaaS.

## 5. Escopo v0

### 5.1 Fundação Mínima

- App novo em futura pasta `bioma/`, com estrutura repo-like dentro deste repositório.
- Frontend separado de API.
- Banco relacional Postgres como fonte de verdade operacional.
- Auth própria simples usando bibliotecas maduras, hash seguro e sessão/cookie HTTP-only. Não inventar criptografia.
- Modelo mínimo: usuário, cliente/tenant, papel, sessão, audit log, recurso visível ao cliente.
- Ambientes separados: local, staging em nuvem e produção em nuvem.

### 5.2 Cockpit Interno EG

- Tela inicial para EG admin com carteira de clientes, status de ClickUp, entregáveis pendentes, relatórios e aprovações.
- Banco de Ideias, Banco de Stack e Banco de Arquitetura reaproveitados como conceito do dashboard legado.
- Página de Engenharia como banco de artefatos: specs, projetos, ADRs futuros, status, dependências e relações.
- Mapa simples de documentos: projeto -> spec -> decisões -> tarefas -> fonte.
- Inventário do legado `/dashboard`: portar, manter temporário, substituir ou descartar.

### 5.3 Client Hub

Inspirado na proposta HM Conexões, mas adaptado para EG:

- login e home do cliente;
- dashboard executivo com status, próximas ações, relatórios recentes e pendências;
- área de documentos/artefatos: briefing, plano, brand book, calendário, proposta, contratos, links e arquivos;
- timeline de entregáveis e aprovações;
- snapshot de score/Raio-X quando existir;
- relatórios publicados pela EG como snapshot, PDF, embed ou registro manual no primeiro corte;
- base visual inspirada nos mockups HM, sem compromisso pixel-perfect e sem copiar o azul HM como padrão EG.

### 5.4 ClickUp Bridge

- Sincronização inicial read-only de workspace/folders/lists/tasks relevantes.
- Mapeamento cliente Bioma -> pasta/lista ClickUp.
- Bioma mostra status limpo para EG e cliente sem expor ruído operacional.
- Escrita do Bioma para ClickUp apenas com aprovação humana no v0: criar tarefa, atualizar status, comentar, anexar link ou marcar entrega.
- Registro de última sincronização, erro, origem, destino e diff resumido.

### 5.5 IA Mínima

- Harness simples para registrar chamadas de IA: provider, modelo, prompt_version, input_schema, output_schema, custo estimado, usuário, cliente e artefato.
- Usos v0: gerar rascunho de brand book, calendário editorial, resumo de relatório ou próximas ações.
- Toda saída de IA é rascunho até aprovação humana.
- OpenSquad continua como ferramenta interna de planejamento/execução, não como dependência runtime da plataforma.

### 5.6 Acessos de Cliente

- V0 não constrói um NordPass.
- V0 deve ter checklist de acessos por cliente e fallback manual seguro.
- O fluxo substitui gradualmente planilhas de usuário/senha por solicitações estruturadas e auditáveis.
- Segredos reais só entram quando houver decisão de cofre/criptografia e modelo de permissão.

## 6. Fora de Escopo v0

- Office pixel art/escritório virtual.
- SaaS público, white-label e reseller hierarchy.
- Billing, cupons, planos, Stripe completo e cobrança automatizada.
- CRM completo substituindo Kommo/ClickUp.
- BI completo com ingestão automática de todas as plataformas.
- LinkedIn Ads/Meta/Google Ads automatizados como requisito do primeiro deploy.
- Chatwoot, WhatsApp omnichannel, VoIP, hub de chips.
- Workspace próprio, drive próprio, e-mail próprio.
- Mobile nativo.
- Micro AWS/provedora de infra própria.
- RAG completo e segundo cérebro em produção.
- Execução autônoma de squads sem HITL.

## 7. Requisitos Funcionais

- **RF-01:** EG admin deve fazer login por e-mail e senha.
- **RF-02:** Cliente deve fazer login por e-mail e senha e ver apenas seus dados.
- **RF-03:** EG admin deve cadastrar cliente mínimo: nome, status, responsável, links e mapeamento ClickUp.
- **RF-04:** Sistema deve listar tarefas/entregáveis vindos do ClickUp por cliente.
- **RF-05:** Sistema deve permitir publicar um documento/relatório para o Client Hub.
- **RF-06:** Sistema deve registrar aprovação/rejeição de cliente com comentário e timestamp.
- **RF-07:** Sistema deve listar artefatos de engenharia por módulo/projeto.
- **RF-08:** Sistema deve expor Banco de Ideias/Stack/Arquitetura em modo útil para operação interna.
- **RF-09:** Sistema deve criar pedido de ação sensível antes de escrever no ClickUp.
- **RF-10:** Sistema deve registrar audit log de login, publicação, aprovação, sincronização e escrita externa.
- **RF-11:** Sistema deve permitir seed de demo HM-like para QA visual e apresentação.
- **RF-12:** Sistema deve registrar chamadas de IA feitas pela plataforma, mesmo que o uso seja pequeno no v0.

## 8. Requisitos Não Funcionais

- **Segurança:** isolamento por cliente, backend como camada de autorização, segredo fora do frontend, cookie seguro e audit log.
- **LGPD:** coletar o mínimo; não enviar dados sensíveis para LLM externa sem regra explícita e aprovação.
- **Performance:** primeira tela interna deve carregar rápido com dados cacheados/sincronizados, não esperando ClickUp em tempo real.
- **Confiabilidade:** sync idempotente; falha de integração aparece como alerta, não como tela vazia.
- **UX:** interface densa, operacional e clara. Sem landing page no produto interno.
- **Portabilidade:** arquivos internos continuam no Git até decisão de migrar bancos para DB.

## 9. Modelo Conceitual v0

- `users`: usuários EG e clientes.
- `organizations`: EG e clientes.
- `memberships`: vínculo usuário-organização-papel.
- `clients`: ficha operacional do cliente.
- `artifacts`: docs, links, specs, relatórios, brand books e calendários publicados.
- `deliverables`: entregas internas ou visíveis ao cliente.
- `approvals`: pedidos e decisões humanas.
- `clickup_mappings`: relacionamento Bioma <-> ClickUp.
- `sync_runs`: histórico de sincronização.
- `ai_runs`: chamadas de IA.
- `audit_logs`: eventos sensíveis.

## 10. Marcos de Entrega

- **M0 - Planejamento travado:** spec, matriz build-vs-buy e ambientes.
- **M1 - Scaffold e ambientes:** `bioma/`, frontend, API, Postgres local, deploy staging.
- **M2 - Auth e clientes:** login, EG admin, client user, clientes e RBAC mínimo.
- **M3 - Cockpit interno:** carteira, bancos internos e engenharia docs map.
- **M4 - ClickUp read:** listar tarefas/entregáveis por cliente.
- **M5 - Client Hub:** home cliente, docs, relatórios, aprovações.
- **M6 - ClickUp write HITL:** criar/atualizar tarefa sob aprovação.
- **M7 - IA rascunho:** gerar artefato simples com logs e aprovação.

## 11. Critérios de Aceite v0

- **CA-01:** Cliente A não acessa dados do Cliente B por URL direta.
- **CA-02:** EG admin cadastra cliente e vincula uma lista/pasta ClickUp.
- **CA-03:** Bioma mostra entregáveis vindos do ClickUp com última sincronização.
- **CA-04:** EG publica um relatório/documento e o cliente acessa no Hub.
- **CA-05:** Cliente aprova ou rejeita um item e a decisão fica auditada.
- **CA-06:** Uma escrita no ClickUp exige aprovação antes de executar.
- **CA-07:** Página Engenharia permite achar specs por módulo e entender relações.
- **CA-08:** Staging e produção usam bancos e segredos separados.
- **CA-09:** Uma chamada de IA gera registro em `ai_runs`.

## 12. Branding EG

O Bioma deve seguir a identidade EverGreen como padrão visual. HM Conexões é referência de fluxo e de expectativa comercial, não referência de marca para o produto EG.

- **Verde Musgo Profundo:** `#09231B`
- **Amarelo Baunilha Claro:** `#FFF4C7`
- **Verde Menta Viva:** `#3AC97B`
- **Tipografia:** Helvetica ou fallback compatível (`Helvetica Neue`, Arial, sans-serif)

Direção visual:

- Produto operacional, premium, claro e denso.
- Evitar depender de roxo/azul escuro como linguagem dominante.
- Usar menta como cor de ação/estado positivo, não como fundo dominante.
- Usar amarelo baunilha para superfícies claras e contraste editorial.
- Usar verde musgo como base institucional, navegação e contraste.
- Telas HM podem inspirar navegação lateral, cartões, dashboard, CRM e calendário, mas a camada visual deve parecer EG.

## 13. Decisões Arquiteturais

ADRs iniciais do MVP v0:

- `adr/ADR-0001-stack-e-deploy.md`: frontend, API, worker, Vercel, Railway e Fly como alternativa posterior.
- `adr/ADR-0002-auth-e-sessao.md`: login/senha, sessão, RBAC mínimo e alternativas de auth.
- `adr/ADR-0003-dados-postgres-e-isolamento.md`: Postgres, modelo mínimo e isolamento por cliente.
- `adr/ADR-0004-clickup-bridge.md`: ClickUp read-only primeiro e escrita sob aprovação humana.
- `adr/ADR-0005-branding-eg.md`: branding EverGreen como padrão visual do Bioma.
- `adr/ADR-0006-lgpd-dpa-e-regiao.md`: DPA, política, região de infra e gate jurídico para produção real.

Ainda pendentes para ADR posterior:

- Estratégia de cofre/criptografia para segredos reais de clientes.
- Como ler bancos internos: arquivo Git, adapter de leitura, DB ou híbrido.
- Modelo final de sync ClickUp: polling, webhook ou ambos.
- Política de IA/LLM para dados sensíveis e custos.
