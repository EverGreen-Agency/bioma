# Auto-melhoria dos Squads (eg_meta)

**Id:** auto-melhoria-squads
**Categoria:** Feature

## O que é
O squad que avalia e aprimora os outros squads. Um loop cibernético onde a IA da EG melhora sua própria inteligência lendo relatórios de erros.

## Detalhe da Absorção
O Runner da pipeline já documenta os problemas e sucessos nos `memories.md` e logs. O `eg_meta` varre esses logs, entende onde um squad específico (ex: Curador) falhou/alucinou, e *escreve uma proposta (diff)* de mudança no prompt (`.agent.md`) desse agente para consertar o gap, dependendo apenas da sua aprovação humana para aplicar.
