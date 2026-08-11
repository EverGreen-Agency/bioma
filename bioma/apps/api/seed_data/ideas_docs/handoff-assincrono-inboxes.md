# Arquitetura de Handoff Assíncrono (Inboxes)

**Id:** handoff-assincrono-inboxes
**Categoria:** Infra

## O que é
O padrão de comunicação interno primário do nosso ecossistema de esquadrões.

## Detalhe da Absorção
Para evitar o "spaghetti de agentes" se chamando diretamente e travando em timeouts, implementamos o padrão Pub/Sub via filesystem. Esquadrões gravam os seus outputs finais em diretórios "Inbox". O `Dispatcher` monitora as caixas de saída e roteia silenciosamente os artefatos para a caixa de entrada do próximo squad da esteira, garantindo desacoplamento robusto.
