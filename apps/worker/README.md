# Bioma Worker

Worker assíncrono e agendável do Bioma. O primeiro uso real é a sincronização do módulo de Performance, portado do BIAds.

## Responsabilidades

- Consumir solicitações `queued` de `sync_runs` com lock transacional no Postgres.
- Sincronizar Google Ads, GA4, Search Console e Google Tag Manager.
- Fazer upsert idempotente nas tabelas diárias por cliente.
- Isolar falhas por provider e concluir a execução como `ok`, `partial` ou `error`.
- Consumir solicitações de conteúdo IA. Sem `OPENAI_API_KEY`, o worker produz somente uma prévia metodológica explicitamente identificada; com a chave, usa a Responses API e Structured Outputs.
- Atualizar a saúde das conexões sem armazenar credenciais em texto puro no banco.

O MVP usa o próprio Postgres como fila durável. Redis/RQ só deve entrar se volume, concorrência ou retry distribuído justificarem uma fila dedicada.

## Agendamento (Railway)

Este serviço roda como **cron job**, não como processo contínuo. O agendamento
fica em **Settings → Cron Schedule** no painel do Railway — não existe no
`railway.json`, então clonar o repositório não reproduz o agendamento.

O comando é `python -m bioma_worker.cli --collect-uptime --enqueue-all --drain`,
e **as flags não são opcionais**:

| Flag | Sem ela |
|---|---|
| `--enqueue-all` | o worker nunca enfileira os syncs agendados |
| `--drain` | processa um job só e para |
| `--collect-uptime` | a disponibilidade medida pelo prober externo nunca é arquivada |

Até 2026-08-07 o `startCommand` não tinha flag nenhuma. Com cron configurado e
sem elas, **nada sincronizaria — e sem erro nenhum**, que é o pior tipo de
falha: um painel que simplesmente não atualiza.

O cron em uso é **de hora em hora**, e é esse número que o heartbeat do Better
Stack precisa espelhar (`BETTERSTACK_HEARTBEAT_URL`). Heartbeat configurado
para um intervalo maior que o cron só reclamaria muito depois do worker ter
parado.

O CLI termina quando esvazia a fila, que é o que o Railway exige de um cron. Se
uma execução ainda estiver rodando na hora da próxima, o Railway pula a rodada
em vez de rodar duas em paralelo.

## Configuração

Copie `../../infra/env/worker.example.env` para `.env` e configure:

- `DATABASE_URL`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `OPENAI_API_KEY` (opcional no ambiente local; obrigatória para geração real)
- `OPENAI_MODEL` (default atual do adapter: `gpt-5.6-sol`)
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID`, quando a conta for acessada por MCC
- `GOOGLE_ADS_API_VERSION`, atualmente `v21` por padrão e configurável sem alterar código

No banco, `performance_connections.credentials_ref` deve apontar para `env:GOOGLE_SERVICE_ACCOUNT_JSON` ou, futuramente, para uma referência de cofre. O JSON da service account não deve ser salvo em `performance_connections`.

## Execução

```bash
python -m venv .venv
pip install -r requirements.txt
python -m bioma_worker.cli
```

Processar toda a fila:

```bash
python -m bioma_worker.cli --drain
```

Enfileirar todos os clientes ativos com janela incremental de três dias e processar:

```bash
python -m bioma_worker.cli --enqueue-all --drain --days 3
```

Esse último comando é o candidato para uma job isolada no Railway. Ele evita duplicar uma execução que já esteja `queued` ou `running` para o mesmo cliente.

## Testes

```bash
python scripts/smoke_worker.py
python scripts/smoke_queue.py
```

`smoke_worker.py` valida normalização e auditoria sem rede. `smoke_queue.py` valida a fila e o encerramento auditável de falha sem usar uma conta Google real.

## Control plane multi-provider

O worker também executa as etapas aprovadas de workflows de IA pelo control
plane do Bioma. Conta, canal de autenticação, modelo e política de roteamento
são entidades separadas. Isso evita confundir uma assinatura de usuário com
uma API faturada separadamente.

Superfícies suportadas:

- `codex_chatgpt`: executa com `codex exec --json` e coleta as janelas de cota
  pelo protocolo estável de `codex app-server`.
- `claude_code`: executa com `claude -p --output-format json`. Como a CLI não
  publica um contrato headless para a cota da assinatura, os snapshots de cota
  são manuais.
- `antigravity_cli`: registra a assinatura Google e suas cotas, mas fica em
  `manual_handoff`; `/usage` e `/quota` são comandos da TUI, sem saída JSON
  documentada para automação segura.
- `antigravity_sdk`, `gemini_api` e `vertex`: executam Gemini de forma
  programática. Essas superfícies usam API key ou ADC/Vertex e não consomem
  automaticamente a cota da assinatura pessoal do Antigravity.

Para habilitar o SDK opcional:

```bash
pip install -r requirements-antigravity.txt
```

Variáveis relevantes:

```dotenv
CODEX_CLI_PATH=codex
CLAUDE_CLI_PATH=claude
AI_EXECUTION_TIMEOUT_SECONDS=600
GEMINI_API_KEY=
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=global
```

As contas guardam somente referências como `env:GEMINI_API_KEY`; o valor da
credencial permanece no ambiente do worker. Canais baseados em assinatura
local exigem que o worker rode na máquina onde a CLI está instalada e
autenticada. Um worker no Railway não herda a sessão local do Codex, Claude ou
Antigravity.

Validação ponta a ponta sem consumir cota real:

```bash
python scripts/smoke_ai_control_plane.py
```
