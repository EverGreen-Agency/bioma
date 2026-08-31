# ADR-0004: ClickUp Bridge

- **Status:** aprovado para MVP v0
- **Data:** 2026-07-09
- **Contexto:** ClickUp continua sendo a ferramenta operacional de PM da EG; Bioma vira plano de controle e hub executivo.

## Decisão

Implementar o ClickUp Bridge em duas fases:

1. **Read-only primeiro:** importar workspace/folders/lists/tasks relevantes e exibir status limpo por cliente.
2. **Write HITL depois:** criar tarefa, atualizar status, comentar ou anexar link somente após aprovação humana.

O Bioma deve mapear cliente -> pasta/lista ClickUp e registrar origem, destino, última sincronização, erro e diff resumido.

## Motivos

- Evita reconstruir PM tool no MVP.
- Entrega valor rápido ao conectar operação real com visão executiva.
- Protege contra automações perigosas em ferramenta operacional.
- Mantém ClickUp como fonte operacional enquanto Bioma vira camada de produto.

## Alternativas Consideradas

- **Substituir ClickUp:** fora de escopo e sem ROI no v0.
- **Escrever automaticamente no ClickUp desde o início:** risco alto de bagunçar operação.
- **Integração manual por link:** simples, mas não resolve a dor central de centralização.

## Consequências

- O MVP precisa de tela de status de integração.
- Toda escrita externa deve gerar `approval` e `audit_log`.
- Sync deve ser idempotente e tolerante a falhas.
- Worker só entra quando polling/webhook/retry justificar.
