# Spec: mod-comunicacao-wpp

- **Cliente:** EverGreen + clientes EG (`target: internal`, com impacto externo)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-comunicacao-wpp`, `log-audio-wpp`, `sla-watchdog`, `centralizacao-comunicacoes`, `telecom-chips`

## 1. Objetivo

Centralizar, registrar e organizar comunicações de WhatsApp relacionadas à operação EG-cliente, reduzindo perda de contexto, atrasos de SLA e dependência de celulares/planilhas.

## 2. Contexto

Hoje grande parte da comunicação com clientes acontece em comunidades e grupos de WhatsApp. Isso é eficiente socialmente, mas ruim para auditoria, memória, SLA, onboarding e continuidade operacional. O módulo deve começar como espelho/organizador e só depois evoluir para automações avançadas.

## 3. Escopo

O que será construído:

- Inbox por cliente/tenant, canal e grupo.
- Registro de mensagens relevantes, anexos e áudios quando permitido.
- Transcrição de áudio e envio curado para `mod-conhecimento`.
- Watchdog de SLA para mensagens não respondidas.
- Mapeamento de grupos por função: geral, gerência, financeiro, social, etc.
- Integração futura com Evolution API/Cloud API conforme ADR.
- Gestão de números/chips apenas como camada operacional, não como empresa telecom no core.
- Resumo de comunicação para `client-hub`.

## 4. Fora de Escopo

- Disparo frio ou automação agressiva sem consentimento.
- Substituir WhatsApp no MVP.
- Construir operadora/chip white-label dentro do core EG.
- Usar API não oficial sem ADR e risco aceito.
- Capturar mensagens privadas sem base legal/consentimento.

## 5. Requisitos Funcionais

- RF1 — Sistema deve associar conversas/grupos a tenant, cliente e contexto operacional.
- RF2 — Sistema deve registrar mensagens relevantes com timestamp e origem.
- RF3 — Áudios marcados devem ser transcritos e associados ao cliente/deal/projeto.
- RF4 — Watchdog deve alertar quando mensagem de cliente ultrapassar SLA configurado.
- RF5 — Sistema deve permitir marcar mensagem como pendência, decisão, briefing ou ruído.
- RF6 — Resumos aprovados devem alimentar `mod-conhecimento`.
- RF7 — Cliente deve ver no Hub apenas comunicações publicadas/resumidas, não bastidores.
- RF8 — Integrações devem registrar status e falhas em `mod-observabilidade`.

## 6. Requisitos Não-Funcionais

- **Privacidade:** consentimento e política clara para captura/transcrição.
- **Segurança:** tokens/sessões em `cofre-senhas`; sem QR/chave em logs.
- **Confiabilidade:** queda de API não pode apagar histórico já salvo.
- **Compliance:** respeitar políticas da Meta e risco de banimento.
- **Operação:** priorizar registro e SLA antes de bot autônomo.

## 7. Critérios de Aceite

- CA1 — Uma conversa é vinculada corretamente a um tenant.
- CA2 — Áudio autorizado é transcrito e aparece na timeline do cliente/deal.
- CA3 — Mensagem sem resposta gera alerta após SLA configurado.
- CA4 — Dados de um grupo de cliente não aparecem para outro tenant.
- CA5 — Falha de conexão WhatsApp aparece em observabilidade.
- CA6 — Mensagem marcada como privada não é enviada ao RAG.

## 8. Riscos e Dependências

- **Risco:** API não oficial gerar banimento ou instabilidade.  
  **Mitigação:** ADR Cloud API vs Evolution/Baileys; começar com leitura/espelho quando possível.

- **Risco:** capturar conversa demais e criar risco LGPD.  
  **Mitigação:** consentimento, escopo, retenção e curadoria.

- **Dependência:** `mod-lgpd-governanca-dados`.
- **Dependência:** `cofre-senhas`.
- **Dependência:** ADR WhatsApp oficial-vs-não-oficial.

