# API externa do Bioma — como um app de fora consome (ex: Fóton)

Este documento existe porque os endpoints de token pessoal estavam prontos e a
tela de geração também, mas **não havia nenhuma documentação de consumo** — para
descobrir o formato do header era preciso ler o código da API.

## 1. Gerar o token

**Onde:** Bioma → **Configurações** → card **"Tokens de Acesso Pessoal"**.

1. Dê um nome que identifique o app (ex: `foton-producao`).
2. Opcionalmente defina validade em dias. Sem validade, o token não expira —
   use isso apenas para app próprio, e revogue quando trocar de máquina.
3. **O token completo aparece uma única vez.** Só o prefixo (16 primeiros
   caracteres) fica visível depois; o resto é guardado como hash.

O token tem o formato `bioma_pat_<44 caracteres>`. O prefixo `bioma_pat_` é
proposital (mesmo padrão do GitHub/Stripe): scanners de segredo reconhecem a
string em log ou commit antes mesmo de saber que é do Bioma.

## 2. Autenticar as chamadas

Header padrão Bearer:

```http
Authorization: Bearer bioma_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Exemplo com `curl`:

```bash
curl -H "Authorization: Bearer $BIOMA_TOKEN" \
     https://<host-da-api>/auth/me
```

Exemplo em Python:

```python
import httpx

client = httpx.Client(
    base_url="https://<host-da-api>",
    headers={"Authorization": f"Bearer {BIOMA_TOKEN}"},
)
me = client.get("/auth/me").json()
```

**Importante:** o token carrega **exatamente as permissões do usuário que o
gerou**. Um token do Eduardo (eg_admin) enxerga tudo que o Eduardo enxerga. Não
existe token com escopo reduzido hoje — ver "Pendências" no fim.

## 3. Endpoints úteis para um app externo

Todos os endpoints da API aceitam o token. O contrato completo e sempre
atualizado está em `bioma/packages/contracts/openapi.json` (gerado por
`scripts/export_openapi.py`) — importe no Insomnia/Postman ou gere um cliente.

Os mais prováveis para um app pessoal:

| Endpoint | O que devolve |
|---|---|
| `GET /auth/me` | usuário, organizações e papéis — bom para testar a conexão |
| `GET /tasks/me` | suas tarefas em todos os workspaces (o que priorizar hoje) |
| `GET /workspaces` | workspaces acessíveis (clientes + operação EG) |
| `GET /clients` | carteira de clientes |
| `GET /backoffice/cockpit-summary` | agregado da carteira: atrasos, aprovações, integrações paradas |
| `GET /backoffice/portfolio-performance?days=30` | investimento por canal e leads, por cliente |
| `POST /copilot` | conversa com o copiloto (mesmo motor da interface) |

## 4. Revogar

Mesma tela, botão de revogar. A revogação é imediata — a próxima chamada com
aquele token recebe 401. Toda criação e revogação vira registro em `audit_logs`.

## 5. Pendências conhecidas

Registradas aqui para não virarem surpresa:

- **Sem escopo por token.** Todo token herda as permissões inteiras do usuário.
  O ideal seria escolher escopos na criação (ex: só leitura, só `tasks`).
- **Sem rate limit próprio.** O rate limit atual (`login_attempts`) cobre login,
  não uso de PAT.
- **Sem rotação assistida.** Trocar um token é criar outro e revogar o antigo na
  mão; não há aviso de expiração próxima.
