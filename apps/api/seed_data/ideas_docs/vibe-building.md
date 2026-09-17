# Vibe Building (blocos reutilizáveis)

**Id:** vibe-building
**Categoria:** Infra

## O que é
A estratégia de componentização do desenvolvimento das ferramentas do OS. Não criamos scripts monstruosos únicos, criamos pequenos legos lógicos.

## Detalhe da Absorção
Blocos funcionais (como o "qualificador de WhatsApp", o "leitor de GA4", a "auditoria de CRM") são instanciados e conectados via Dispatcher. Em vez de reescrever lógica, reaproveitamos os módulos. É o equivalente de ter componentes no frontend, mas aplicados à lógica de agentes.
