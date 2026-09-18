# Contas pagas no control plane de IA

## Regra de segurança

- Cadastre a conta com `auth_ref` vazio para canais de assinatura (`codex_chatgpt`, `claude_code`, `antigravity_cli`).
- Conclua o login oficial pelo botão **Entrar com ChatGPT/Claude/Google**. Não cole senha, cookie ou token em chat, issue, commit ou campo livre.
- API e worker devem receber a mesma `SECRET_ENCRYPTION_KEY` pelo gerenciador de secrets do runtime. O bundle cifrado só é materializado durante probe, coleta ou execução e é removido ao final.
- Para canais por API, `auth_ref` aceita somente `env:NOME` ou `vault:IDENTIFICADOR`; o valor fica fora do banco e do Git.

## Sequência de ativação

1. Crie a conta como `inactive` ou sem política preferencial.
2. Faça o login oficial e execute **Probe do runtime**. O probe não deve gerar conteúdo.
3. Colete a cota. Codex e Antigravity permitem leitura sem inferência; a cota do Claude pode exigir uma resposta mínima e a interface deve deixar esse consumo explícito.
4. Carregue o catálogo de modelos e abra a prévia de rota. Cota medida, política de rota e execução real são evidências diferentes.
5. Autorize uma geração curta, com marcador único, e confira provider, modelo, tokens, custo, id externo e tentativa gravada.
6. Só então habilite a conta nas políticas operacionais.

## Prova de 2026-09-17 neste host

| Canal | Runtime | Sessão | Inferência |
|---|---|---|---|
| Codex/ChatGPT | `codex-cli 0.154.0-alpha.6.2` | não autenticada | não iniciada |
| Claude Code | `2.1.198`, assinatura Pro | autenticada por `claude.ai` | tentativa única recusada por conexão; 0 tokens, custo 0 |
| Google Antigravity | executável ausente | não verificada | não iniciada |

O Postgres local e o Docker não estavam disponíveis. A tentativa do Claude passou pelo executor real `execute_candidate`, mas não houve seleção persistida pelo roteador nem registro em `ai_execution_attempts`. Portanto, esta rodada valida runtime e falha controlada; não comprova uma rota concluída.
