# Bioma API

Backend HTTP do Bioma MVP v0.

Responsabilidades iniciais:

- auth e sessão;
- escopo por cliente;
- descoberta persistente de workspaces por tenant;
# Bioma API

Backend HTTP do Bioma MVP v0.

Responsabilidades iniciais:

- auth e sessão;
- escopo por cliente;
- descoberta persistente de workspaces por tenant;
- CRM/funil de leads;
- financeiro mínimo;
- métricas manuais/analytics honesto;
- audit log;
- motor nativo de projetos, contratos, escopo, tarefas e entregas;
- cofre de acessos cifrado e auditado;
- radar de oportunidades por captura manual, fontes RSS públicas e feeds configuráveis;
- **Auto-Vigilância & Auditoria Automática de Perfil por URL (`profile_auditor.py`)**;
- **Injeção Automática de Cases & Provas Sociais nas Propostas (`attached_cases`)**;
- **Inventário de Gaps Tecnológicos do Mercado (`opportunity_skill_gaps` e `tech_skill_inventory`)**;
- **Big Data Comercial & Analytics de ROI/CAC por Plataforma**;
- importador ClickUp legado, sem superfície de sincronização no produto;
- publicação de artefatos para o Client Hub;
- healthcheck para staging e produção.

Deploy do MVP: Railway, com root directory `bioma/apps/api` e `railway.json`.

## Banco local

Com o Docker do Bioma rodando:

```bash
python scripts/migrate.py
python scripts/seed_dev.py
python scripts/create_eg_client.py
```

Usuários de desenvolvimento:

- `eduardo@evergreengrowth.com.br` / `senha-dev-123`
- `henrique@hmconexoes.com.br` / `senha-dev-123`

## Rodar local

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn bioma_api.main:app --reload
```

## Validar

```bash
python -m compileall bioma_api scripts
python scripts/smoke_api.py
python scripts/smoke_clickup.py
python scripts/smoke_projects.py
python scripts/smoke_vault.py
python scripts/smoke_workspace_authz.py
python scripts/smoke_workspace_navigation.py
python scripts/smoke_tasks.py
python scripts/smoke_copilot.py
```

Os smokes criam massa efêmera própria e não dependem do cliente HM no banco compartilhado. A matriz cobre health, CORS, login, CRUD, archive/purge auditado, navegação, capacidades e isolamento BOLA/IDOR entre clientes.

`smoke_tasks.py` cobre EG admin, operator, viewer e client_user; cliente A tentando ler e mutar cliente B; CRUD, subtarefas, dependências, recorrência idempotente e imutabilidade de projeções ClickUp.

Também valida `GET /workspaces`: o EG admin recebe o workspace interno e os clientes; `client_user` recebe somente seu próprio contexto. O smoke cobre ainda membership legada indevida na organização EG, bloqueio de convite ao workspace interno e revogação de Client Hub, Files, Performance e Kommo quando um workspace cliente é arquivado. `create_eg_client.py` mantém temporariamente o adapter exigido pelos módulos da Operação EG, mas esse registro não aparece como workspace cliente.

Client Hub, CRM, financeiro, métricas, arquivos, convites e Performance também estão expostos por `/workspaces/{workspace_id}/...`. As rotas `/clients/{client_id}/...` permanecem durante a transição. A migration `0013_performance_workspace_context.sql` faz backfill e dual-write do UUID canônico e reserva `gtm_workspace_id` para o identificador textual externo do Google Tag Manager.

Carteiras e autorização usam `tenant_memberships`, `teams`, `team_memberships` e `workspace_assignments`. O acesso efetivo é resolvido uma única vez por workspace, com papéis `tenant_admin`, `workspace_manager`, `operator`, `approver`, `viewer` e o adapter legado `client_user`. A gestão administrativa está em `/teams`, `/tenants/{tenant_id}/members` e `/workspaces/{workspace_id}/assignments`.

Preferências do navegador ficam em `workspace_favorites` e `workspace_saved_views`. A descoberta em `GET /workspaces` informa `is_favorite` e `is_assigned`; favoritos usam `/workspaces/{id}/favorite` e visões salvas usam `/workspaces/views`.

The Estúdio IA usa `POST /workspaces/{id}/ai/content` para enfileirar e `GET` no mesmo caminho para histórico/resultados. A API não chama o modelo dentro da requisição HTTP; o worker processa `ai_content_requests` e audita em `ai_runs`.

Pesquisa de mercado usa `GET/POST /workspaces/{id}/market-research`, `POST /workspaces/{id}/market-research/refine` e `GET /workspaces/{id}/market-research/{research_id}`. O serviço aceita somente o workspace interno da EG: é inteligência para uma vertical de prospecção, não conteúdo do Hub. Leitura exige `view`; refinamento e geração exigem `manage_work`. O worker usa `OPENAI_RESEARCH_MODEL` (padrão `gpt-5.6-terra`), Structured Outputs e pesquisa web. Chamadas externas não mantêm transação aberta, e fontes declaradas pelo modelo só sobrevivem se também estiverem no retorno nativo da ferramenta.

O contexto estruturado do cliente usa `GET/PATCH /workspaces/{id}/client-profile`. Leitura exige `view`; alteração exige `manage_work`, é auditada e atualiza um único perfil por workspace de cliente. A completude retornada é derivada dos campos persistidos, não aceita valor enviado pelo cliente.

`/backoffice/ai-operations` é exclusivo de EG admin e oferece FinOps de IA, catálogo/instalação de workflows, runs idempotentes, aprovação e conclusão ordenada de etapas. A migration `0029_ai_operations_finops.sql` não inclui seed. O smoke `scripts/smoke_ai_operations.py` valida assinatura, cota, ledger, idempotência e HITL apenas em banco `_smoke`/`_test`.

O Bioma é o system of record da execução. O importador legado classifica listas ClickUp como `social`, `growth`, `tech` ou `general` e preserva IDs externos para reconciliação. Tarefas importadas continuam somente leitura para não reescrever o histórico; trabalho novo é nativo do Bioma.

`smoke_clickup.py` valida o cliente ClickUp com `httpx.MockTransport`, sem chamar a API real.

`smoke_github_read.py` valida, também sem rede, a projeção de issues, PRs e commits. O mapping projeto Tech → `owner/repository` é tenant-scoped; `view` consulta e `manage_work` configura. A leitura real exige `GITHUB_API_TOKEN`.

## Encerramento do ClickUp

Não configure novo token para uso cotidiano. `scripts/import_clickup_to_bioma.py` permanece temporariamente como ferramenta de migração env-only, tenant-scoped, transacional por pasta e idempotente por `external_id`. Depois do snapshot e da reconciliação com projetos/escopo nativos, endpoint, configuração, adapter e colunas legadas devem ser removidos em etapas verificáveis.

## Projetos e cofre

`projects` segue router → service → repository e exige `view` para leitura e `manage_work` para escrita. A intake de planejamento é um recurso interno do projeto: rascunho pode ser criado/alterado com `manage_work`, só finaliza após validação servidora e fica imutável; `client_user` não a recebe. `retail_v1` valida campos comerciais e a compatibilidade entre maturidade e meta. Ao gerar, `planning_intake_id` precisa apontar para uma intake finalizada do mesmo projeto e a fotografia normalizada segue para o squad e para `project_plans.intake_snapshot`. O planejador cria versões a partir de contrato, briefing ou onboarding. Novos `project_plan_items` nascem com `selected=false`; `PATCH /project-plan-items/{id}` permite à equipe editar o candidato somente no rascunho e audita os campos alterados. Aprovação usa capability `approve`, recusa `client_user` e exige ao menos um item selecionado. Materialização usa `manage_work`, lock, filtra `selected=true` e mantém mapeamento por item para replay sem duplicar entregas. A resposta de cliente contém somente itens selecionados e visíveis de planos já aprovados/materializados. Documentos Tech podem receber `contract_id` e `planning_excerpt`; o serviço valida a pertença ao projeto e fornece ao planejador somente documentos gerais ou daquele contrato. URL não dispara busca nem leitura externa. O subdomínio Tech adiciona fases, documentos, atualizações e candidatos GitHub; Growth e Social usam o mesmo plano sem escrita GitHub. `smoke_projects.py` cobre papéis, BOLA cliente A→B, owner, escopo/fase cruzados, contrato, entrega, ritmo, feed Tech e auditoria.

`vault` exige `SECRET_ENCRYPTION_KEY`, guarda ciphertext versionado, separa `submit_secrets`, `manage_secrets` e `reveal_secrets`, e audita criação, rotação, status, revelação e cópia. O registro suporta plataforma, conta/perfil, usuário, e-mail, senha, outra forma de acesso e link; somente o link é metadado legível. `smoke_vault.py` cobre a matriz de acesso e deve apontar para banco isolado.

`DELETE /clients/{client_id}` arquiva cliente e workspace, preservando o histórico. O purge físico é separado em `POST /clients/{client_id}/purge`, exclusivo de EG admin, exige confirmação exata do nome, limpa objetos S3 antes do banco e mantém o evento `client.purged` na auditoria.

## Endpoints HM/MVP

- `GET/POST/PATCH/DELETE /clients/{client_id}/leads`
- `GET/POST/PATCH/DELETE /clients/{client_id}/finance`
- `GET/POST/PATCH/DELETE /clients/{client_id}/metrics`

## Endpoints de Prospecção, Radar & Big Data (`/backoffice/proposals`)

- `GET /backoffice/proposals/opportunities`: Lista oportunidades varridas.
- `POST /backoffice/proposals/opportunities/ingest`: Triagem manual de vaga.
- `POST /backoffice/proposals/opportunities/sync`: consulta as três fontes RSS públicas e feeds adicionais configurados.
- `POST /backoffice/proposals/opportunities/{id}/generate`: Gera proposta em 3 pilares com injeção de cases.
- `GET /backoffice/proposals/catalog`: Catálogo server-owned `commercial_proposal_v1`.
- `POST /backoffice/proposals/from-brief`: Valida cliente ativo, combina perfil + briefing, executa os três pilares e persiste snapshot e modo `live`/`preview`.
- `GET/POST/PATCH /backoffice/proposals`: Gerenciador de propostas comerciais (status `draft`, `approved`, `sent`, `negotiating`, `won`, `lost`).
- `GET /backoffice/proposals/platforms`: Lista e configura custos de assinaturas SaaS de plataformas.
- `GET/POST/DELETE /backoffice/proposals/profiles`: Gerencia perfis para auto-vigilância.
- `POST /backoffice/proposals/profiles/sync`: Raspa e audita perfil freelancer por URL pública.
- `GET /backoffice/proposals/skills`: Lista competências e cases do acervo EG.
- `GET /backoffice/proposals/gaps` e `POST /gaps/{gap_id}/resolve`: Gerencia e incorpora gaps tecnológicos ao acervo.
- `GET /backoffice/proposals/analytics`: Retorna métricas de Big Data (Win Rate %, CPP, CAC, Lucro Líquido e ROI % por canal).

`commercial_proposals.workspace_id` é opcional para compatibilidade com o radar externo, mas obrigatório no fluxo de briefing. A migration 0055 adiciona série/versão, campos estruturados e `intake_snapshot`; não é aplicada automaticamente. O repositório usa whitelist de colunas mutáveis, evitando que chaves arbitrárias do payload componham SQL dinâmico.

### Lifecycle comercial e Copiloto

- `GET /backoffice/proposals/{id}`: detalhe interno com revisões, eventos, entregas e conversão.
- `PUT /backoffice/proposals/{id}/content` e `POST /claims-review`: edição em rascunho e revisão HITL.
- `POST /backoffice/proposals/{id}/transition`: única entrada para transições explícitas de status.
- `POST /revisions`, `POST /deliveries`, `DELETE /{id}`: nova versão, evidência de entrega e archive.
- `GET /{id}/pdf`: PDF gerado somente após claims aprovadas.
- `POST /{id}/convert`: conversão idempotente e confirmada em projeto, contrato e escopo.
- `GET /backoffice/proposals/cohorts`: coortes por mês e tempos do funil.
- `GET/POST /proposals/public/{token}/detail|accept`: visualização pública reduzida e aceite explícito.
- `/backoffice/sales-copilot`: sessões, preparação, eventos manuais, conclusão e métricas; `/realtime-adapter` declara `not_configured`.
- `GET /backoffice/planning-portfolio`: portfólio EG de intakes e planos por cliente/projeto.

A migration 0056 cria essas estruturas e amplia o check de `project_planning_intakes`; ela deve ser aplicada explicitamente no ambiente escolhido.

### Migrations 0057 e 0058

- `0057_sales_copilot_meeting_intelligence.sql`: configuração de reunião, consentimento/retenção, token de ingestão com hash, participantes, segmentos diarizados, sugestões e ações HITL.
- `0058_github_activity_project_updates.sql`: snapshots idempotentes de atividade GitHub publicados como `project_updates`.

Rotas adicionais do Copiloto:

- `PUT /backoffice/sales-copilot/{id}/meeting`;
- `POST /backoffice/sales-copilot/{id}/participants`;
- `POST /backoffice/sales-copilot/{id}/transcript-segments`;
- `POST /backoffice/sales-copilot/{id}/analyze-live`;
- `POST /backoffice/sales-copilot/{id}/actions`;
- `POST /backoffice/sales-copilot/actions/{action_id}/materialize`;
- `POST /backoffice/sales-copilot/{id}/ingestion-credential`;
- `POST /backoffice/sales-copilot/ingest/{id}` com `X-Copilot-Ingest-Token`.

O último endpoint não usa sessão de usuário: autentica o adaptador por token rotacionável, exige consentimento e nunca retorna o conteúdo da sessão. O bot/STT é externo e ainda precisa ser selecionado.

### Experience V2 — migration 0106

`0106_experience_v2_foundation.sql` é aditiva e liga conversa, oportunidade,
reunião, proposta, tarefa, documentação e evidência sem trocar as fontes de
verdade existentes.

- `GET/PATCH /backoffice/proposals/opportunities/{id}` e
  `POST /backoffice/proposals/opportunities/{id}/activities|contacts` expõem a
  continuidade comercial e sua timeline;
- sessões de `/backoffice/sales-copilot` podem receber `opportunity_id`;
- `/workspaces/{workspace_id}/work-graph` cria itens e relações de
  rastreabilidade; relações nunca concedem acesso;
- `POST /workspaces/{workspace_id}/requests` permite ao cliente solicitar um
  resultado sem acessar tarefas internas; a equipe atualiza a triagem por
  `PATCH /requests/{request_id}`;
- tarefas separam `description` (contexto), `acceptance_criteria` e
  `definition_of_done`; registros legados copiados para DoD ficam marcados com
  `semantic_review_required` até revisão humana;
- respostas do Copilot persistem `response_blocks` tipados e as threads podem
  ser vinculadas a múltiplas entidades.

O OpenAPI é parte do corte e deve continuar sincronizado com
`python scripts/export_openapi.py --check`.

### Backlog, importação documental e jornada — migration 0107

`0107_backlog_document_imports_and_sales_journey.sql` torna `work_items` o
backlog canônico, adiciona preview/materialização HITL de HTML de projeto e
grava o funil/jornada derivados das reuniões comerciais. A especificação,
user stories, Definition of Done e limites operacionais estão em
[`SPEC-BACKLOG-IMPORTACAO-JORNADA-V1.md`](../../../docs/SPEC-BACKLOG-IMPORTACAO-JORNADA-V1.md).
