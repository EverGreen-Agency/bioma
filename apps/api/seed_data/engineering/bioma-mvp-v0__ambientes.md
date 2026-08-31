# Ambientes - Bioma MVP v0

- **Data:** 2026-07-09
- **Status:** rascunho aprovado para planejamento
- **Objetivo:** separar desenvolvimento local, staging em nuvem e produção em nuvem desde o início.

## 1. Topologia

Estrutura alvo quando for codar:

```text
bioma/
  apps/
    web/      # frontend navegável
    api/      # backend HTTP/API
    worker/   # backend assíncrono/jobs opcionais
  packages/
    contracts/ # schemas/clients gerados ou compartilhados
  infra/
    docker-compose.yml
    env/
```

### Padrão de nomenclatura

- `apps/web`: app web navegável, ou seja, o frontend que o usuário acessa.
- `apps/api`: serviço HTTP de backend, responsável por regras, permissões, integrações, auditoria e persistência.
- `apps/worker`: processo de backend assíncrono para jobs, webhooks, retries, IA e sincronizações.

Usei `web` e `api` porque eles nomeiam processos implantáveis, não apenas camadas conceituais. `Backend` continua sendo o domínio técnico maior; dentro dele podem existir `api`, `worker`, `scheduler` e comandos de migração. Se a EG preferir nomes mais literais, a alternativa é `apps/frontend` e `apps/backend`, mas eu manteria `web/api/worker` por ser mais claro em monorepos e deploys.

## 2. Ambientes

### Local

Uso: desenvolvimento no notebook.

- Frontend rodando local.
- API rodando local.
- Postgres local via Docker.
- Redis local apenas quando worker existir.
- Seeds com dados fake: EG demo, cliente HM-like demo e tarefas ClickUp fake.
- Sem credenciais reais de cliente.
- ClickUp inicialmente em modo sandbox/read-only ou mock.

### Staging

Uso: testar com URL real antes de produção.

- Frontend na Vercel em ambiente preview/custom `staging`.
- API em Railway com domínio de staging.
- Banco Postgres separado de produção.
- Redis separado se houver worker.
- Secrets de staging separados.
- Integrações externas com apps/contas de teste quando possível.
- Dados anonimizados ou fake por padrão.

### Produção

Uso: EG e clientes reais.

- Frontend na Vercel production.
- API em Railway production.
- Worker separado quando houver sync/IA/relatório recorrente.
- Postgres production com backup.
- Secrets production com acesso restrito.
- Monitoramento e alertas mínimos.

## 3. Fluxo de Deploy

- `develop` -> staging.
- `main` -> produção.
- Pull request pode gerar preview de front.
- Migração de banco deve ser comando/pipeline explícito, não efeito colateral invisível.
- Promoção para produção exige checklist: testes, migração, env vars, backup, rollback.

## 4. Variáveis de Ambiente

Padrão mínimo:

```text
APP_ENV=local|staging|production
WEB_BASE_URL=
API_BASE_URL=
DATABASE_URL=
REDIS_URL=
SESSION_SECRET=
ENCRYPTION_KEY=
CLICKUP_CLIENT_ID=
CLICKUP_CLIENT_SECRET=
CLICKUP_WEBHOOK_SECRET=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
SENTRY_DSN=
LOG_LEVEL=
```

Regras:

- Nunca reutilizar segredo de produção no local.
- Nunca commitar `.env`.
- Chaves de staging e produção devem ser rotacionáveis.
- Frontend só recebe variáveis públicas.
- Backend e worker recebem segredos.

## 5. Railway vs Fly

Decisão recomendada para o MVP v0: **Railway primeiro para API, Postgres, Redis e worker; Fly como alternativa técnica para uma fase posterior**.

Motivo:

- A urgência atual é colocar o Bioma no ar com staging e produção separados, sem montar uma operação de infraestrutura pesada.
- Railway encaixa melhor no MVP por reduzir atrito em serviços web, banco, variáveis, ambientes e deploys rápidos.
- Fly é tecnicamente forte quando a prioridade é controle fino de runtime, região, rede privada, máquinas e topologias mais específicas.
- Como o frontend fica na Vercel, a decisão real é onde hospedar o backend e os serviços de apoio. Para o primeiro corte, Railway tende a dar mais velocidade com menos carga operacional.

Critério de revisão:

- Reavaliar Fly quando houver exigência real de multi-região, baixa latência por região, runtime muito controlado, rede privada mais complexa ou custo/limite do Railway começar a pesar.

## 6. Workers

Não criar worker por hábito. Criar quando alguma tarefa tiver uma destas características:

- demora mais que uma requisição normal;
- precisa retry/backoff;
- roda por agenda;
- recebe webhook;
- chama LLM com custo/latência relevante;
- sincroniza ClickUp/Ads/Drive;
- não pode falhar silenciosamente.

Primeiros candidatos:

- sync ClickUp;
- processamento de webhook ClickUp;
- geração de relatório/brand book/calendário;
- importação manual/CSV;
- observabilidade de integrações.

## 7. Checklist de Produção Mínima

- HTTPS em todos os domínios.
- Banco production separado.
- Backup automático e teste de restore documentado.
- Logs sem segredo/PII sensível.
- Sentry ou equivalente para erros.
- Healthcheck da API.
- Painel simples de status de integrações.
- Seed de admin EG criado por comando seguro.
- Nenhuma credencial real em arquivo, Git ou frontend.
- Política clara de rollback.

## 8. Referências

- Vercel environments: https://vercel.com/docs/deployments/environments
- Railway environments: https://docs.railway.com/environments
- Railway pricing: https://docs.railway.com/pricing/plans
- Fly pricing: https://fly.io/docs/about/pricing/
- Fly secrets: https://fly.io/docs/apps/secrets/

Leitura: Vercel separa ambientes Local, Preview e Production, com variáveis por ambiente e custom environments em planos Pro/Enterprise. Railway possui ambientes por projeto para isolar configuração e deploy. Fly gerencia secrets criptografados por app via `fly secrets`, injetados como variáveis em runtime.
