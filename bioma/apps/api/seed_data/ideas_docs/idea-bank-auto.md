# Banco de Ideias auto-atualizável

**Id:** idea-bank-auto
**Categoria:** Cockpit

## O que é
Avanço do ciclo de vida das ideias, passando de humano-dependente para autônomo reativo.

## Detalhe da Absorção
Um Reconciliador lê a estrutura de pastas do projeto, status de cards no ClickUp e merges no GitHub. Se ele detecta que os scripts da ideia "tag-ativacao" existem e rodam na branch principal, ele move automaticamente o card do Kanban de "desenvolvimento" para "pronto". Reduz trabalho de manutenção.
