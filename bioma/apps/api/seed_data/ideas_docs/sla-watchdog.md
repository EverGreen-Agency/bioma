# SLA Watchdog (WhatsApp)

**Id:** sla-watchdog
**Categoria:** Feature

## O que é
Um cão de guarda automatizado que garante o tempo de resposta em grupos de WhatsApp com clientes.

## Detalhe da Absorção
O agente lê passivamente os grupos via Evolution API. Se o cliente manda uma mensagem e nenhum humano da equipe responde dentro da janela de SLA (ex: 30 minutos em horário comercial), o bot dispara um alerta no Slack/WhatsApp interno para os diretores.
