# Conectar o Bioma ao ChatGPT

Serve para conversar no ChatGPT (na sua assinatura, sem gastar API) e o ChatGPT
ler e escrever no Bioma: buscar tarefa, criar, atualizar, comentar.

**A direção importa.** O ChatGPT *chama* o Bioma. Isso **não** faz o copiloto de
dentro do Bioma rodar na assinatura do ChatGPT — ele continua precisando de
chave de API ou das CLIs de assinatura. O ganho é você trabalhar dentro do
ChatGPT e o Bioma continuar sendo o sistema de registro.

## Onde isso funciona (corrigido em 2026-08-06)

A primeira versão deste documento dizia "ChatGPT Web → Developer mode → custom
connector". **Estava errado.** Aquilo veio de artigos de terceiros; a
documentação oficial (`learn.chatgpt.com/docs/extend/mcp`) diz o contrário:

| Superfície | Conecta servidor MCP próprio? |
|---|---|
| **App desktop** | **Sim, direto** — Configurações → MCP servers → Add server |
| ChatGPT Web | **Não diretamente.** Web usa *plugins* |
| Plugin (web ou desktop) | Sim, mas exige **ChatGPT Work** e passa por publicação/revisão na OpenAI |

**Use o app desktop.** É o caminho oficial, não precisa publicar nada, não
precisa de plano Work, e aceita exatamente o que o Bioma expõe: transporte
**Streamable HTTP** e autenticação por **Bearer token**.

Pré-requisito: a API do Bioma publicada em **HTTPS** (já está, na Railway).
Não precisa de túnel — túnel só serviria para testar contra `localhost`.

## 1. Gerar seu token pessoal

No Bioma: **Configurações → Tokens de Acesso Pessoal → Gerar token**. Ou pela API:

```bash
curl -X POST https://api.bioma.<seu-dominio>/auth/personal-access-tokens \
  -H "Content-Type: application/json" \
  -b "bioma_session=<seu-cookie>" \
  -d '{"name": "ChatGPT desktop"}'
```

O token aparece **uma vez** (`bioma_pat_...`). Guarde na hora.

O ChatGPT passa a enxergar exatamente o que **você** enxerga — o token carrega
suas permissões, não mais que isso. Revogar o token corta o acesso na hora.

## 2. Adicionar o servidor no app desktop

**Configurações → MCP servers → Add server:**

| Campo | Valor |
|---|---|
| Nome | `Bioma` |
| Tipo | **Streamable HTTP** (não STDIO — o Bioma é remoto) |
| URL | `https://api.bioma.<seu-dominio>/mcp` |
| Autenticação | **Bearer token** |
| Token | o `bioma_pat_...` do passo 1 |

Salve e escolha **Restart**.

Se o tipo ou a autenticação não baterem, o ChatGPT rejeita **em silêncio** — se
o servidor não listar ferramenta nenhuma, é quase sempre isso.

## 4. Testar

Numa conversa nova, com o conector ligado:

> Liste meus workspaces no Bioma.

Depois:

> Crie no workspace Operação EG uma tarefa "Revisar proposta da Univet",
> prioridade Alta, com definição de pronto "proposta revisada e enviada".

Escrita exige confirmação manual na conversa — é o ChatGPT que impõe isso, e
está de acordo com a regra do copiloto (ação que sai do Bioma sempre pede
confirmação).

## Ferramentas expostas

| Ferramenta | O que faz |
|---|---|
| `search` | Busca tarefa por texto. **Nome fixo da OpenAI** — é o que o ChatGPT usa para citar fonte. |
| `fetch` | Abre um item pelo id (`task:<uuid>`). **Nome fixo da OpenAI.** |
| `bioma_list_workspaces` | Workspaces que você acessa |
| `bioma_list_tasks` | Tarefas de um workspace |
| `bioma_create_task` | Cria tarefa |
| `bioma_update_task` | Atualiza tarefa |
| `bioma_add_task_comment` | Comenta (nasce interno) |

Não renomeie `search` e `fetch`: o contrato é da OpenAI, e o conector quebra
sem barulho se os nomes ou os campos mudarem.

## Como a autorização funciona

Toda ferramenta chama a **camada de serviço** do Bioma, nunca o banco direto.
Consequência: não existe política de acesso separada para revisar aqui. Se você
não pode criar tarefa num workspace pela tela, também não pode pelo ChatGPT,
pelo mesmo código.

Quando falta permissão, a ferramenta devolve o **motivo real** ("Seu papel
neste workspace não permite esta ação"), não um erro genérico — para o ChatGPT
conseguir te dizer o que fazer.

## Se der errado

| Sintoma | Causa provável |
|---|---|
| Conector não lista ferramenta | Modo de autenticação errado, ou token inválido/revogado |
| 401 | Token expirado ou revogado — gere outro |
| Não acha uma tarefa que existe | Ela é interna (`client_visible=false`) e seu papel é de cliente |
| Cria tarefa mas não aparece na tela | Confira o workspace: o padrão do status é `Backlog` / `NOT_STARTED` |

## Limites conhecidos

- **Só tarefas por enquanto.** Proposta, wiki e cliente ainda não estão
  expostos — `search` cobre tarefa apenas.
- **Sem rate limit próprio** neste endpoint. O login tem; este não. Aceitável
  para uso pessoal com token seu, mas é o primeiro item a endurecer se o
  conector for compartilhado.
- **`search` varre workspace por workspace** em vez de uma query só, de
  propósito: é a camada de serviço que aplica a visibilidade. Com a carteira
  atual o custo é irrelevante; com centenas de clientes precisa de índice.
