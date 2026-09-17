# Arquitetura do Bioma — mapa para humanos e IAs

Leia antes de mexer no código. Este projeto **não é Next.js**: o frontend é
Vite + React Router (rotas declaradas em `App.tsx`, sem `page.tsx`/pastas-rota)
e o backend é FastAPI síncrono com Postgres.

## Backend (`apps/api/bioma_api/`)

Toda feature segue a **trinca por domínio**:

```text
routers/<dominio>.py       # casca HTTP fina: valida tipos (UUID!), delega
services/<dominio>.py      # regra de negócio, permissões, auditoria
repositories/<dominio>.py  # SQL puro, sempre parametrizado
```

Domínios: `auth`, `oauth`, `passwords`, `invites`, `workspaces`, `client_hub`, `projects`, `tasks`, `vault`, `performance`,
`files`, `kommo` (routers `integrations`/`analytics`), `admin` (= backoffice EG,
prefixo `/backoffice`). Transversais: `access.py` (papéis, membership,
feature-gating), `crypto.py` (segredos em repouso), `config.py` (env),
`migrations/*.sql` (só aditivas, aplicadas no boot por `scripts/start.py`).

O domínio `ai_content` persiste ativações por workspace e não publica conteúdo automaticamente. A API apenas enfileira; o worker escolhe o job mais antigo entre Performance e IA, registra execução em `ai_runs` e produz saída estruturada. Sem credencial externa, o modo local é explicitamente `preview`; com `OPENAI_API_KEY`, o adapter usa a Responses API com JSON Schema estrito.

O domínio `market_research` usa a mesma separação router → service → repository e persiste versões em `market_researches`, com fontes normalizadas em `market_research_sources`. Ele é exclusivo do workspace interno da EG e apoia a prospecção de uma vertical; não é conteúdo de Hub e não possui publicação para cliente. O vínculo `workspace → tenant_organization_id` é validado pelo serviço e por trigger no banco. Chamadas ao provedor acontecem fora da transação; somente o resultado final ou a falha são persistidos depois. No modo `live`, o worker combina Structured Outputs com pesquisa web, aceita como citáveis apenas URLs observadas no retorno nativo do provedor e exige um conjunto mínimo de fontes. O modo `preview` não contém afirmações factuais nem referências.

O domínio `client_profiles` persiste um único contexto estruturado por workspace de cliente em `workspace_client_profiles`. A leitura usa `view`, a alteração usa `manage_work` e cada alteração gera evento de auditoria. A completude é derivada no serviço, nunca gravada como valor manual. Ao gerar um plano de projeto, o serviço carrega esse contexto por organização e o inclui no snapshot do planejador; o worker só produz rascunho e não materializa fases ou entregas sem aprovação.

O domínio interno `ai_operations` é o control plane dos fluxos da EG. Templates em código são instalados como definições versionadas; cada execução usa chave de idempotência, materializa etapas em ordem e volta a `pending_approval` nos checkpoints interativos. Completar uma etapa pode registrar uso/custo, mas o motor não executa escrita externa nem pula HITL. Os primeiros fluxos são proposta, onboarding nativo no Bioma, LinkedIn e entrega Tech.

Propostas comerciais não possuem um cadastro paralelo de cliente. `commercial_proposals.workspace_id` aponta para o mesmo workspace usado por perfil, projetos e contratos. O catálogo `commercial_proposal_v1` vive no servidor e valida tipo, modalidade, urgência e serviços; o briefing e o contexto do cliente são fotografados em `intake_snapshot`. A geração usa os três pilares e grava `generation_mode=live|preview`, mas não cria contrato, projeto, entrega nem envio externo. Essas transições pertencem ao ciclo de vida posterior e exigem confirmação HITL e idempotência.

FinOps de IA separa três fatos: `ai_provider_subscriptions` representa compromisso financeiro; `ai_usage_events` representa consumo observado; `ai_quota_snapshots` representa uma medição de capacidade com origem declarada. Valores financeiros usam centavos. Moedas não são somadas entre si e uma execução não aceita custo de etapa em moeda diferente. Autenticação em Codex, Claude ou AntiGravity não é tratada como API de quota: sem dado oficial/configurado, o saldo permanece desconhecido.

## Modelo de produto e tenancy

O destino canônico é:

```text
Bioma Platform
└── Tenant / Agência
    ├── Workspace agency_internal
    └── Workspaces client
```

Glossário:

- **Tenant:** agência assinante/operadora, como EG ou futura agência white-label.
- **Workspace:** fronteira operacional e de dados; pode ser interno da agência ou de cliente.
- **ClientAccount:** vínculo comercial que aparece na carteira; nunca representa a operação interna da agência.
- **Team / Membership / WorkspaceAssignment:** modelo futuro de pessoas, times e carteiras atribuídas.

Decisão completa: [`docs/adr/0001-tenant-workspace-hierarchy.md`](docs/adr/0001-tenant-workspace-hierarchy.md).

Integrações operacionais seguem [`docs/adr/0002-clickup-kommo-integration-strategy.md`](docs/adr/0002-clickup-kommo-integration-strategy.md): o Bioma é a fonte de verdade de projetos e execução; ClickUp é apenas fonte legada de migração, sem sincronização exposta na UI. Kommo, GitHub, SleekFlow e providers de Performance entram como adapters substituíveis, tenant-scoped e auditados. `project_github_connections` mapeia um projeto Tech para `owner/repository`; a API projeta issues, PRs e commits e permite criar uma issue a partir de uma entrega com autorização de workspace, confirmação explícita, reserva local, marcador de reconciliação e auditoria. Escritas externas adicionais continuam condicionadas a idempotência e HITL.

O domínio `projects` materializa `workspace → project → project_contracts → contract_scope_items → project_planning_intakes → project_plans → project_plan_items → project_phases → deliverables`, com `project_documents` e `project_updates` como registros de acompanhamento. Uma intake é um contexto pontual e versionado, não outro cadastro de cliente: começa em rascunho, é validada por esquema servidor (`retail_v1` inicial), torna-se imutável ao finalizar e deixa sua fotografia no plano gerado. As metas de marketing e comercial são condicionadas à maturidade; a API rejeita uma meta incompatível, em vez de aceitar estado obsoleto do navegador. Um documento pode apontar para um contrato específico e conservar um `planning_excerpt` confirmado; o serviço valida que o contrato pertence ao mesmo projeto e inclui apenas documentos gerais ou daquele contrato no snapshot do planejador. URL é referência navegável, não evidência de leitura automática de conteúdo privado. Contrato e plano são versionados. Cada saída da IA nasce como candidato não selecionado; a equipe pode ajustar fase, título, descrição, prazo, prioridade, definição de pronto, subtarefas, visibilidade e aceite enquanto o plano está em rascunho. Aprovação exige ao menos um candidato selecionado e a materialização idempotente ignora todos os rejeitados. Planos antigos são preservados como selecionados pela migration. A listagem de `client_user` contém somente itens selecionados, visíveis e de planos aprovados/materializados. Tech, Growth e Social usam o mesmo motor, mas somente Tech marca tarefas elegíveis ao adapter GitHub. Conclusão e aceite continuam sinais distintos. O banco valida coerência de projeto, contrato, escopo, plano e entrega por FKs, checks e triggers.

O domínio `vault` guarda somente ciphertext `enc:v1:` para usuário, e-mail, senha, outro método de acesso, token, códigos de recuperação e notas. Plataforma, conta/perfil e link são metadados; a listagem nunca devolve segredos. Revelação/cópia exige capability específica, motivo e auditoria. Cliente pode depositar credenciais para o próprio workspace sem obter permissão de revelação. O frontend descarta o segredo revelado após 60 segundos, mas esse TTL de UI não substitui controles de servidor.

O domínio `tasks` segue a trinca completa: o router só traduz HTTP, o service aplica capacidades e invariantes, e `repositories/tasks.py` concentra todo SQL. Leituras exigem `view`; listas e mutações exigem `manage_work`. Assignee, owner e dependencies são resolvidos dentro do mesmo tenant/workspace, ciclos são rejeitados e a recorrência usa uma chave de origem única para ser idempotente.

Estado transitório: `workspaces` fornece a identidade persistente e `GET /workspaces` faz a descoberta autorizada. Os domínios operacionais aceitam `/workspaces/{workspace_id}/...`; `/clients/{client_id}/...` permanece como adapter de compatibilidade. Performance mantém `client_id` e `workspace_id` em dual-write enquanto leitores e workers migram, e o identificador externo do GTM chama-se `gtm_workspace_id`. `subject_organization_id` ainda aponta para o contêiner físico dos dados e `clients` continua como extensão comercial 1:1. `EverGreen Internal` fornece somente a ponte técnica da Operação EG e não pode ser removido antes das FKs/adapters restantes. `parent_organization_id` e `tenant_organization_id` descrevem pertencimento, mas não concedem autorização hierárquica. A carteira é uma projeção de `workspace_assignments`: atribuições podem apontar diretamente para usuário ou time, e `workspace_access_role(...)` centraliza a precedência dos papéis.

Regras invioláveis:

1. **Todo endpoint tem auth explícita** (`Depends(current_user_from_request)`).
   Endpoint público é exceção documentada (convite/reset/oauth/health).
2. **Todo acesso a dados de cliente passa por `find_accessible_client` ou
   `check_organization_access`** (BOLA/IDOR) e respeita `enabled_modules`
   (`require_client_module`) para `client_user`.
3. **Nenhum segredo em texto puro no banco** — `crypto.encrypt_secret`
   (Fernet, `SECRET_ENCRYPTION_KEY`); segredos nunca voltam em resposta HTTP.
4. **IDs em path são `UUID` tipado**, nunca `str`.
5. Scripts utilitários vivem em `scripts/` e usam `bioma_api.db.connect`
   (nunca connection string hardcoded). Cada domínio tem `smoke_<dominio>.py`.

## Frontend (`apps/web/src/`)

```text
App.tsx                # TODAS as rotas declaradas aqui
lib/api.ts             # único cliente HTTP (request/requestText); nunca fetch cru
hooks/useBiomaApi.ts   # react-query por cima do api.ts (cache/mutações)
store/uiStore.ts       # zustand só para estado de UI (seleções, drafts)
views/<X>View.tsx      # telas de cliente/EG-operação
views/admin/<area>/    # backoffice EG (lazy obrigatório — Phaser pesa 1,4 MB)
components/            # compartilhados; types/ para tipos de domínio do backoffice
styles.css             # design system (tokens EG); inline style é exceção
```

Mapa de acesso atual (quem vê o quê):

| Camada | Rotas | Guarda |
|---|---|---|
| Público | `/` (login), `/convite/:token`, `/redefinir/:token`, `/privacidade` | nenhuma |
| Control Plane EG | `/`, `/clientes` | sessão + `guardAdmin()` quando administrativo |
| Operação EG | `/operacao`, `/operacao/crm`, `/operacao/financeiro`, `/operacao/metricas` | `guardAdmin()` + ponte exata da organização EG |
| Workspace cliente | `/clientes/:id`, `/contexto`, `/projetos`, `/tarefas`, `/acessos`, `/crm`, `/financeiro`, `/analytics`, `/documentos`, `/integracoes` | cliente acessível + gate do módulo daquela organização |
| Backoffice EG | `/engenharia`, `/eg-office`, `/eg-ideas`, `/eg-tech`, `/eg-architecture`, `/configuracoes` | `guardAdmin()` + lazy-load |

Regras invioláveis:

1. **Nada de `fetch()` cru** — todo request passa por `lib/api.ts` (base URL de
   produção + cookies + erros padronizados).
2. **Nada de dado mockado apresentado como real** — estado vazio honesto ou
   badge "demo"; "em breve" só para feature declarada, nunca número inventado.
3. **View nova = lazy no `App.tsx`** se não for a rota inicial.
4. **Variável CSS nova nasce no `:root` do `styles.css`** — referenciar token
   inexistente falha em silêncio (já aconteceu duas vezes).
5. **URL/contexto é a fonte da verdade operacional.** Componentes podem ser compartilhados entre EG e clientes, mas toda consulta/mutação recebe workspace explícito; `selectedClientId` é apenas ponte legada de UI.
6. **Carteira não é navegador de módulos.** A troca em escala acontece pelo navegador pesquisável do Topbar; a Sidebar e as tabs mostram apenas o contexto corrente.
7. **DELETE de cliente significa archive.** Purge físico é uma operação separada de platform admin, exige o cliente já arquivado e confirmação exata do nome, remove objetos S3 antes do banco e preserva o evento de auditoria.

## Ciclo comercial, planejamento e Copiloto

- `commercial_proposals` continua sendo o agregado de proposta; a migration 0056 acrescenta conteúdo canônico, claims revisáveis, timestamps do funil e aceite.
- `proposal_events`, `proposal_deliveries` e `proposal_conversions` separam auditoria, evidência de envio e efeito operacional. Status não pode ser alterado pelo `PATCH` genérico.
- A superfície pública usa um DTO reduzido e só expõe proposta revisada, não arquivada, vigente e já enviada/em negociação/ganha.
- A conversão de proposta ganha exige confirmação HITL e chave idempotente; cria projeto, contrato e itens de escopo numa transação. O refinamento do backlog continua no planejador versionado.
- `project_planning_intakes` aceita variantes server-owned por disciplina: `retail_v1`, `tech_v1` e `growth_social_v1`. Respostas finalizadas ficam congeladas; planos continuam candidatos até aprovação/materialização.
- O Copiloto persiste sessões e eventos internos. Preparação e pós-call usam o worker seguro; o modo atual recebe transcrição/notas manuais. Realtime é somente uma porta de adapter e permanece `not_configured` até haver provider, orçamento, consentimento e política de retenção.

## Protocolo de sessão (humano ou IA)

1. `git status` antes de começar; uma frente por sessão.
2. UI-only significa UI-only: precisou de backend, **pare e liste o que falta**.
3. Antes de encerrar: `npx tsc -b` + `npm run build` (web), `compileall` +
   boot da API + smoke do domínio tocado (api). **Nunca deixar o tree quebrado.**
4. Commit pequeno por marco, mensagem em PT, sem co-author de IA.
5. Decisões de escopo vão para `ROADMAP-MVP.md`; fila operacional em
   `EXECUCAO-MVP.md`.

## Inteligência de reunião

O Copiloto separa quatro responsabilidades:

1. **adaptador de reunião:** Meet/Teams ou upload envia segmentos por contrato autenticado; o Bioma não assume um fornecedor;
2. **diarização:** `external_speaker_id` preserva a identidade técnica e pode ser associado a participante, organização, cargo, senioridade e papel decisório;
3. **assistência:** uma janela limitada da conversa é cruzada com snapshot versionado de cliente, proposta e pesquisa, gerando sugestões com referências aos segmentos;
4. **execução:** resumo e compromissos permanecem propostas internas até confirmação HITL; só então criam tarefa, revisão ou atualização de projeto.

O token de ingestão é retornado uma vez e somente seu SHA-256 é persistido. Ingestão externa requer consentimento concedido. O transporte web atual é polling; a entrada automática de bot e o STT são adapters externos ainda não escolhidos.

Na conversão comercial, o projeto/contrato é confirmado primeiro. A geração do plano ocorre depois do commit, em outra transação; indisponibilidade do worker gera evento de falha sem corromper ou reverter o contrato.
