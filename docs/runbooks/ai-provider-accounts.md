# Contas pagas no control plane de IA

## Regras de segurança

- Cadastre a conta com `auth_ref` vazio para canais de assinatura (`codex_chatgpt`, `claude_code`, `antigravity_cli`).
- Conclua o login oficial pelo botão **Entrar com ChatGPT/Claude/Google** na UI. Nunca cole senha, cookie ou token em chat, issue, commit ou campo livre.
- API e worker compartilham estritamente a mesma `SECRET_ENCRYPTION_KEY` injetada via gerenciador de secrets (Vault, Doppler, AWS Secrets Manager ou Docker Compose).
- O bundle de credenciais cifrado só é materializado em diretório temporário efêmero (`tempfile.mkdtemp` com permissão restrita) durante o probe, coleta ou execução, sendo obrigatoriamente deletado via `shutil.rmtree` ao final do contexto.
- Para canais por API direta (`openrouter`, `deepseek`, `gemini_api`), `auth_ref` aceita somente `env:NOME` ou `vault:IDENTIFICADOR`; os segredos nunca entram no banco de dados nem no Git.

---

## 1. Configuração da Chave Simétrica (`SECRET_ENCRYPTION_KEY`)

A chave é simétrica (Fernet AES-128-CBC + HMAC-SHA256) codificada em 32 bytes URL-safe base64. Ambos os containers (`apps/api` e `apps/worker`) validam o formato na inicialização via Pydantic validator e falham o boot se a chave for inválida ou divergente.

### Gerar nova chave
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Injetar no ambiente (Linux / Docker)
No arquivo `.env` de produção ou no secret manager:
```bash
SECRET_ENCRYPTION_KEY="<chave_gerada_acima>"
```

No `docker-compose.yml`:
```yaml
services:
  api:
    environment:
      - SECRET_ENCRYPTION_KEY=${SECRET_ENCRYPTION_KEY}
  worker:
    environment:
      - SECRET_ENCRYPTION_KEY=${SECRET_ENCRYPTION_KEY}
```

---

## 2. Provisionamento dos CLIs no Servidor / Container do Worker

Para que o worker execute ferramentas locais de assinatura, os binários oficiais devem estar presentes no PATH do container do worker.

### Dockerfile do Worker (Exemplo Linux Alpine/Debian)
```dockerfile
# Node.js LTS para Codex e Claude Code
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @openai/codex @anthropic-ai/claude-code \
    && npm cache clean --force

# Antigravity CLI (agy)
# Copiar binário homologado ou baixar da release oficial interna:
COPY vendor/bin/agy /usr/local/bin/agy
RUN chmod 755 /usr/local/bin/agy
```

### Validação de PATH e Permissões
Verifique no container do worker:
```bash
docker compose exec worker which codex claude agy
docker compose exec worker codex --version
docker compose exec worker claude --version
docker compose exec worker agy --version
```

---

## 3. Probes de Runtime com Custo Zero (Sem Inferência)

O worker implementa probes estritos que inspecionam o ambiente e a validade da autenticação sem gerar tokens ou incorrer em custos:

| Canal | Comando de Versão | Comando de Status (Custo Zero) | Interpretação |
|---|---|---|---|
| `codex_chatgpt` | `codex --version` | `codex login status` | Retorna `0` quando logado; não envia mensagens ao modelo. |
| `claude_code` | `claude --version` | `claude auth status` | Retorna JSON com `{ "loggedIn": true, "authMethod": "..." }`. |
| `antigravity_cli` | `agy --version` | `agy -p /usage` | Lê porcentagem restante da cota semanal/5h sem criar turns de conversa. |
| `openrouter` / `deepseek` | N/A | Verificação de env (`OPENROUTER_API_KEY`, etc.) | Validação em memória sem disparar request HTTP. |

Se um CLI não for encontrado, o painel do Bioma exibe as instruções de instalação e o caminho verificado (`runtime_surface: worker`).

---

## 4. Ciclo de Vida de Credenciais Efêmeras

Quando um job de probe, cota ou inferência é disparado:
1. O worker faz o select da conta no banco Postgres.
2. A função `provider_process_environment(account, settings)`:
   - Cria um diretório temporário isolado (`tempfile.mkdtemp(prefix="bioma_prov_")`).
   - Decifra o `credential_bundle` usando a `SECRET_ENCRYPTION_KEY`.
   - Grava os arquivos estruturados em subpastas dedicadas (`CODEX_HOME` para Codex, `CLAUDE_CONFIG_DIR` para Claude).
   - Injeta as variáveis de ambiente no processo do subprocesso.
3. Ao término (seja por sucesso ou exceção), o bloco `finally` executa `shutil.rmtree` no diretório temporário. Nenhuma sessão em texto plano persiste em disco após a execução.

---

## 5. Auditoria Imutável e Rastreamento (`request_hash`)

Toda execução de IA via roteador ou Copilot é rastreada na tabela `ai_execution_attempts`:

- `request_hash`: Hash SHA-256 (64 caracteres) computado de forma determinística a partir do payload canônico da entrada/prompt.
- `provider`: Provedor real utilizado (`openai`, `anthropic`, `google`, `openrouter`, `deepseek`).
- `model`: Modelo exato executado.
- `status`: `running`, `completed` ou `failed`.
- `input` / `output`: Payload JSONB imutável para compliance.
- `error_code` / `error_message`: Registrado em caso de falha antes de fallback para o próximo candidato.
- `quota_before`: Snapshot das cotas disponíveis no instante do despacho.
- `latency_ms`: Duração total da chamada em milissegundos.

### Consulta de Auditoria no Banco
```sql
SELECT 
    a.id,
    a.started_at,
    a.request_hash,
    a.status,
    p.channel,
    a.account_id,
    a.selection_reason->>'task_kind' as task_kind,
    s.output->'usage' as token_usage,
    s.output->'latency_ms' as latency_ms
FROM ai_execution_attempts a
JOIN ai_accounts p ON p.id = a.account_id
LEFT JOIN ai_workflow_step_runs s ON s.id = a.step_run_id
ORDER BY a.started_at DESC
LIMIT 20;
```

---

## 6. Checklist de Ativação em Produção

1. [ ] `SECRET_ENCRYPTION_KEY` definida e idêntica em API e Worker.
2. [ ] Migração `0111_ai_execution_request_hash.sql` e `0112_ai_free_providers_and_budgets.sql` aplicadas no Postgres.
3. [ ] Binários dos CLIs instalados e no PATH do worker.
4. [ ] No painel do Bioma, executar **Testar runtime** (Probe) para confirmar `ready: true`.
5. [ ] Coletar cota inicial para registrar os buckets de limite.
6. [ ] Executar teste controlado no Copilot com prompt de validação e conferir registro com `request_hash`.

---

## 7. Provedores Gratuitos Nativos (FreeLLMAPI Presets)

O Bioma suporta mais de 10 provedores com camadas gratuitas ativas (Groq, Cerebras, SambaNova, Mistral, Together, Cohere, GitHub Models, Cloudflare, DeepInfra, Novita e canal genérico `openai_compatible`).

### Características Técnicas
- **Nativo no Worker**: Sem dependência de daemons de terceiros; chamadas executadas nativamente via `httpx` para endpoints compatíveis OpenAI `/chat/completions`.
- **Pool de Chaves Cifradas**: Chaves salvas na tabela `ai_provider_key_pool` com encriptação Fernet via `SECRET_ENCRYPTION_KEY`.
- **Fallback para Env Vars**: Caso não haja chave no banco, o worker busca automaticamente a variável de ambiente correspondente (`GROQ_API_KEY`, `CEREBRAS_API_KEY`, `SAMBANOVA_API_KEY`, etc.).
- **Rotação Automática em 429**: Ao receber `HTTP 429` (Rate Limit), a chave ativa é colocada em cooldown automático por 60 segundos e o worker tenta a próxima chave do pool ou o próximo provedor gratuito elegível da política.

---

## 8. FinOps & Governança de Orçamentos Granulares

A tabela `ai_organization_budgets` permite controle financeiro e operacional em tempo real por organização:

- **Teto Mensal de Tokens (`monthly_token_cap`)**: Limite máximo de tokens processados no mês civil.
- **Teto Mensal de Custo (`monthly_cost_cap_cents`)**: Limite financeiro em centavos de dólar/real.
- **Limiar de Alerta (`alert_threshold_percent`)**: Notificação ao atingir a porcentagem configurada (ex: 80%).
- **Hard-Stop Obrigatório (`enforce_hard_stop`)**:
  - Quando ativado e o consumo mensal ultrapassar 100% de qualquer um dos tetos, novas chamadas de workflow no worker são bloqueadas preventivamente com `BudgetExceededError`.
  - Provedores com custo zero (como os gratuitos do FreeLLMAPI) continuam operacionais se o bloqueio for exclusivamente por teto de custo, preservando a continuidade operacional sem custos adicionais.

