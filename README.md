# Bioma MVP v0 & Mega-Plataforma

[![Disponibilidade da API](https://uptime.betterstack.com/status-badges/v3/monitor/2uma8.svg)](https://uptime.betterstack.com/?utm_source=status_badge)

<!-- O selo reflete o monitor EXTERNO de `api.bioma.evergreenmkt.com.br/health/ready`.
     Ele diz `up`/`down` agora — o histórico e a janela de 90 dias ficam em
     /operacao/prova, que lê `uptime_snapshots`. Selo é imagem servida pelo
     provedor: se ele cair, vira ícone quebrado. Por isso não é a fonte do
     número, só um atalho visual. -->

Bioma é a plataforma operacional e motor comercial da EverGreen. O sistema reúne cockpit interno EG, Client Hub, motor nativo de projetos/tarefas, contratos e escopo, cofre de acessos, radar de oportunidades por captura manual e feeds RSS verificáveis, auditoria assistida de perfis por URL, inventário de gaps tecnológicos, métricas comerciais, auth, Postgres e adapters externos.

## Modelo de produto

O Bioma evolui em três camadas: primeiro organiza a operação interna da EG, depois permite operar e atender clientes diretamente e, por fim, torna a mesma base disponível para outras agências em white-label/SaaS.

```text
Bioma Platform (control plane da dona do produto)
└── Tenant / Agência (EG ou futura agência white-label)
    ├── Workspace interno da agência
    └── Workspaces de clientes
```

O MVP já possui identidade persistente em `workspaces` e descoberta autenticada por `GET /workspaces`. `organizations` continua como contêiner físico dos dados e `clients` como fachada comercial/ponte das rotas ainda baseadas em `client_id`. A interface diferencia o workspace interno da EG dos hubs, mas equipes, atribuições e papéis white-label completos ainda não estão implementados. `bioma-legacy/` não é fonte da arquitetura ativa.

## Estrutura

```text
bioma/
  apps/
    web/      # app web React/Vite
    api/      # API HTTP FastAPI
    worker/   # jobs assíncronos, quando necessário
  packages/
    contracts/ # contratos OpenAPI/schemas compartilhados
  infra/
    docker-compose.yml
    env/
  DEPLOY.md       # staging, produção e rollback
  EXECUCAO-MVP.md # fila operacional entre LLMs
```

Uso `web` e `api` porque são nomes de deploy e runtime: a interface publicada na Vercel é o app web, e o backend publicado no Railway é a API HTTP. Na prática, `web` equivale ao frontend e `api` equivale ao backend.

## Stack decidida

- Frontend: React + Vite + TypeScript.
- Backend: FastAPI + Python.
- Banco: Postgres direto.
- Fila atual: Postgres (`sync_runs`). Redis permanece opcional para uma evolução futura.
- Deploy definido para o MVP: Vercel para `apps/web`; Railway para API, Postgres e jobs futuros. Redis não é necessário no staging atual.
- Fly fica como alternativa futura se houver exigência real de região Brasil, runtime ou rede.

## Branding

- Verde Musgo Profundo: `#09231B`
- Amarelo Baunilha Claro: `#FFF4C7`
- Verde Menta Viva: `#3AC97B`
- Tipografia: Helvetica ou fallback compatível.

## Desenvolvimento local

1. Copie os arquivos de ambiente:

```bash
cp infra/env/api.example.env infra/env/api.local.env
cp infra/env/web.example.env infra/env/web.local.env
cp infra/env/worker.example.env infra/env/worker.local.env
```

2. Suba banco e Redis locais:

```bash
docker compose -f infra/docker-compose.yml up -d
```

O Docker do banco/Redis não precisa ser recriado a cada mudança de código. Ele fica rodando como infraestrutura local. Recrie quando mudar `infra/docker-compose.yml`, trocar imagem, alterar porta, resetar volume ou quando quiser usar o perfil de app.

Para rodar também API e web via Docker:

```bash
docker compose -f infra/docker-compose.yml --profile app up --build
```

O perfil `app` constrói imagens locais para API e web. Na primeira execução ele baixa imagens base e dependências (`pip install`, `npm ci`), então depende de rede estável. Para desenvolvimento diário, o caminho mais rápido continua sendo Docker apenas para Postgres/Redis e API/web rodando no host com reload.

Se o build Docker falhar em `npm ci` com `ETIMEDOUT`, é falha de rede durante instalação de dependências dentro do container. Rode novamente quando a conexão estabilizar ou use `npm install`/`npm run dev` no host.

3. API:

```bash
cd apps/api
python -m venv .venv
pip install -r requirements.txt
python scripts/migrate.py
python scripts/seed_dev.py
python scripts/create_eg_client.py  # ponte temporária da Operação EG
uvicorn bioma_api.main:app --reload
```

4. Web:

```bash
cd apps/web
npm install
npm run dev
```

5. Worker de Performance:

```bash
cd apps/worker
python -m venv .venv
pip install -r requirements.txt
python -m bioma_worker.cli --drain
```

O worker usa `sync_runs` no Postgres como fila durável. A API responde `202 queued`; o processamento Google ocorre fora da requisição HTTP. Para um agendamento incremental, use `python -m bioma_worker.cli --enqueue-all --drain --days 3` em uma job isolada no Railway, somente depois da validação das contas Google.

Para executar o worker sob demanda no Docker:

```bash
docker compose -f infra/docker-compose.yml --profile worker run --rm worker
```

Usuários de desenvolvimento:

- `eduardo@evergreengrowth.com.br` / `senha-dev-123`
- `henrique@hmconexoes.com.br` / `senha-dev-123`

## Storage de arquivos (FILE-001)

Upload de documentos usa um bucket S3-compatible (Cloudflare R2, Backblaze B2 ou AWS S3). Sem as variáveis `STORAGE_S3_*` configuradas, os endpoints de upload/download retornam `503` de forma controlada — o resto da API continua funcionando.

Variáveis (`infra/env/api.local.env`): `STORAGE_S3_BUCKET`, `STORAGE_S3_REGION`, `STORAGE_S3_ENDPOINT_URL`, `STORAGE_S3_ACCESS_KEY_ID`, `STORAGE_S3_SECRET_ACCESS_KEY`, `STORAGE_S3_FORCE_PATH_STYLE`, `STORAGE_MAX_UPLOAD_MB`.

Para testar localmente sem credenciais de nuvem, suba um MinIO (S3-compatible) com o perfil `storage`:

```bash
docker compose -f infra/docker-compose.yml --profile storage up -d storage
```

Console em `http://localhost:9001` (usuário `bioma-local` / senha `bioma-local-secret`). Crie o bucket `bioma-dev-files` (uma vez) e aponte a API para ele:

```bash
STORAGE_S3_BUCKET=bioma-dev-files
STORAGE_S3_REGION=us-east-1
STORAGE_S3_ENDPOINT_URL=http://localhost:9000
STORAGE_S3_ACCESS_KEY_ID=bioma-local
STORAGE_S3_SECRET_ACCESS_KEY=bioma-local-secret
STORAGE_S3_FORCE_PATH_STYLE=true
```

## Validação

API:

```bash
cd apps/api
python scripts/migrate.py
python scripts/seed_dev.py
python scripts/smoke_api.py
python scripts/smoke_clickup.py
python scripts/smoke_workspace_authz.py
python scripts/smoke_workspace_navigation.py
python scripts/smoke_tasks.py
python scripts/smoke_performance.py
python scripts/smoke_files.py  # exige STORAGE_S3_* configurado (ver seção Storage acima)
```

Worker:

```bash
cd apps/worker
python scripts/smoke_worker.py
python scripts/smoke_queue.py
```

Frontend:

```bash
cd apps/web
npm run build
```

Os smokes de workspace, tarefas, projetos e cofre criam organizações/workspaces efêmeros próprios; não dependem do cliente HM presente no seed. O Bioma é o system of record da execução. O importador ClickUp fica temporariamente apenas para reconciliar o legado; itens importados preservam IDs externos e permanecem somente leitura até serem convertidos em registros nativos. Não há sync ClickUp na interface nem escrita externa.

## Operações e custos de IA

A Operação EG possui um control plane para instalar workflows versionados e solicitar execuções com idempotência, etapas ordenadas e aprovação humana. O dashboard Financeiro da EG também controla assinaturas/API, custos mensais equivalentes, cotas observadas e consumo por provedor/modelo. Cotas sem fonte oficial ou configuração explícita aparecem como desconhecidas; o produto não deduz saldo da sessão autenticada.

O smoke `apps/api/scripts/smoke_ai_operations.py` recusa bancos que não terminem em `_smoke` ou `_test`.

## Inteligência de mercado

O Estúdio de Pesquisa fica exclusivamente na Operação EG, em `operacao/pesquisa-mercado`. Ele serve para escolher e dominar uma vertical de prospecção antes de abordá-la: setor e recorte geográfico são refinados em focos selecionáveis, e a pesquisa gera um relatório versionado com mercado, processo comercial, dores, referências, terminologia, oportunidades de Growth/Social e roteiro de prospecção. A execução `live` usa pesquisa web, persiste as fontes consultadas e rejeita URLs citadas que não tenham sido devolvidas pelo provedor; sem credencial, o modo `preview` descreve somente a estrutura metodológica e não se apresenta como evidência factual.

Pesquisa de mercado não cria clientes, não povoa o banco e não é publicada no Hub do cliente. O uso de tokens é enviado ao ledger de FinOps; quando não existe uma tabela de preço verificável para modelo e pesquisa web, o custo permanece desconhecido. A exportação inicial usa a impressão/PDF do navegador, preservando a mesma versão exibida na tela.

## Contexto do cliente

Cada Hub possui `contexto`, um onboarding estruturado com informações básicas, contato, negócio, marketing e recursos/preferências. A completude é calculada somente pelos campos efetivamente preenchidos. Leitura exige `view`; edição exige `manage_work` e gera auditoria. Esse contexto é distinto da pesquisa de prospecção e entra como insumo explícito do planejador de projetos, que continua produzindo apenas rascunhos sujeitos à aprovação interna.

Projetos conectam contrato versionado, itens de escopo, intake de planejamento, plano de execução versionado, fases, entregas e aceite. A intake não duplica o cliente: é um rascunho persistido de contexto por iniciativa, finalizado de forma imutável e fotografado no plano que a IA gerou. A primeira variante (`retail_v1`) inclui sinais comerciais e metas de marketing/comercial condicionadas à maturidade; o servidor valida a combinação, inclusive se o navegador estiver desatualizado. O planejador parte de contrato, briefing ou onboarding e gera um backlog candidato identificado como `live`/`preview`. Cada sugestão nasce desmarcada e pode ser revisada com prioridade, definição de pronto e subtarefas; a equipe seleciona o que faz sentido, aprova e somente então materializa os itens escolhidos de forma idempotente. Tech, Growth e Social compartilham o núcleo; Social permite escolher o momento de aprovação e somente Tech produz candidatos a issue GitHub. Em projetos Tech, proposta e especificação podem ser vinculadas por URL ao contrato correto; um trecho/resumo confirmado pode ser marcado para o planejador, que o combina com o escopo e o contexto técnico digitado para produzir o rascunho. O Bioma não afirma ter lido documentos privados apontados apenas por URL. O cliente acompanha somente o plano aprovado/selecionado e as atualizações de progresso, bloqueio, testes e release — inclusive quando um dia foi gasto somente depurando um problema. A área Acessos substitui planilhas: conta/plataforma, usuário, e-mail, senha, outra forma de acesso e link. E-mail, usuário, senha e outro método são cifrados antes do banco; listagens não contêm segredos e revelações/cópias são auditadas. Rode `python scripts/smoke_projects.py` e `python scripts/smoke_vault.py` somente contra banco de teste isolado e migrado.

Projetos Tech podem ser ligados a um repositório GitHub. O painel consulta issues, pull requests e commits recentes e pode criar uma issue a partir de uma entrega somente com `manage_work`, confirmação HITL e auditoria. A escrita usa reserva local e marcador estável no título para recuperar replays após falhas entre GitHub e banco.

## Prospecção B2B, Auto-Vigilância & Big Data de Conversão

O módulo de Propostas Comerciais (`/backoffice/proposals`) opera como a central de atração e conversão B2B da EverGreen:

1. **Radar de Oportunidades & Plataformas B2B**: captura manual e consulta explícita de feeds RSS públicos de Freelancer.com.br, WeWorkRemotely e Remotive, além de feeds configurados pela EG. O scoring atual é determinístico por regras; o rascunho de proposta consome os runners dos três pilares (Oferta, Conversão e Demanda).
2. **Briefing de carteira**: o wizard seleciona ou cria o cliente pelo fluxo canônico, preserva título, tipo, contratada, equipe, modalidade, serviços e contexto comercial e usa o perfil já cadastrado na geração. O snapshot `commercial_proposal_v1` acompanha a proposta; nenhum cliente duplicado é criado.
3. **Integração Financeira de SaaS**: Custos mensais de assinaturas configurados por plataforma geram lançamentos automáticos de despesa recorrente no módulo **Financeiro (`financial_records`)**.
4. **Auditoria por link de perfil (`profile_auditor.py`)**: o scraper tenta extrair informações públicas e retorna erro verificável quando a fonte bloqueia ou falha; o sistema não persiste score ou recomendações fictícias.
5. **Cases e provas sociais**: `attached_cases` permanece vazio até existir uma biblioteca de cases aprovada com origem e resultados verificáveis; inventário de habilidades não é tratado como prova de case.
6. **Inventário de Gaps Tecnológicos**: Identifica automaticamente ferramentas do mercado (HubSpot, Marketo, Salesforce, Shopify, etc.) exigidas em vagas triadas (`opportunity_skill_gaps`), permitindo a incorporação ao portfólio (`tech_skill_inventory`) com 1 clique.
7. **Big Data, ROI & CAC por Plataforma**: Acompanhamento de conversão (Win Rate %), Custo por Proposta (CPP), Custo de Aquisição de Cliente (CAC), Receita Ganha, Lucro Líquido e ROI (%) por canal de prospecção.

A migration 0055 versiona o briefing estruturado. A migration 0056 acrescenta o lifecycle comercial, entregas, conversões e sessões do Copiloto; nenhuma delas é aplicada automaticamente.

O ciclo local agora cobre detalhe editável em Markdown, revisão HITL de alegações, revisões, PDF canônico, transições/timeline auditadas, link público com aceite explícito, archive, coortes e conversão idempotente de proposta ganha em projeto/contrato/escopo. “Envio” só é marcado quando um humano confirma a ação externa; não há integração de e-mail ou assinatura eletrônica apresentada como ativa.

O planejador usa intakes server-owned por disciplina (`retail_v1`, `tech_v1`, `growth_social_v1`) e mantém candidatos separados de entregas materializadas. O Copiloto de Vendas opera no modo preparação + notas/transcrição manual + pós-call; realtime continua não configurado.

Excluir um cliente pela API cotidiana arquiva cliente e workspace. O purge físico é uma ação separada e confirmada, com limpeza S3 e auditoria preservada.


## Comunicação Web/API

O MVP usa REST com contratos tipados no frontend (`apps/web/src/lib/api.ts`) e FastAPI no backend. Isso foi escolhido porque o produto ainda é mais operacional do que exploratório: login, projetos, contratos, escopo, aprovações, cofre, artefatos, adapters e auditoria são comandos explícitos.

GraphQL pode entrar depois como BFF ou camada de consulta se surgirem telas com múltiplas visões altamente customizáveis, overfetching real ou muitos consumidores externos. A decisão atual preserva essa opção porque o frontend não chama `fetch` direto espalhado pela aplicação; ele passa por um cliente HTTP isolado.

## Observação

`bioma-legacy/` permanece como referência histórica, mas não dita stack, arquitetura ou UX deste MVP.

## Reuniões comerciais e Tech

O backoffice possui um Copiloto de reuniões: prepara contexto, registra participantes e papéis, recebe transcrição diarizada manual ou por adaptador, sugere intervenções e converte compromissos confirmados em trabalho. Meet/Teams são origens suportadas pelo contrato de ingestão; ainda não há alegação de que um bot esteja conectado a essas plataformas sem provedor configurado.

Projetos Tech podem publicar um snapshot confirmado da atividade GitHub como atualização compreensível no hub do cliente. A leitura não vira progresso automaticamente.
