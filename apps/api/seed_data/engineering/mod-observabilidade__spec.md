# Spec: mod-observabilidade

- **Cliente:** EverGreen, equipe técnica e status externo (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-observabilidade`, `qa-auditor`, `sla-watchdog`

## 1. Objetivo

Garantir que o Bioma não falhe silenciosamente: monitorar aplicação, banco, filas, integrações, jobs, webhooks, qualidade de dados e experiência mínima dos usuários.

## 2. Contexto

Uma plataforma B2B premium precisa detectar falhas antes do cliente. Quedas de API, token expirado, job parado, webhook perdido, dashboard vazio ou erro de frontend têm impacto direto em percepção de valor e operação.

## 3. Escopo

O que será construído/integrado:

- Health checks de aplicação, banco, Redis, storage e workers.
- Monitoramento de uptime e status page.
- Captura de erros frontend/backend.
- Logs estruturados por tenant, usuário, módulo, job e correlation id.
- Monitoramento de filas, retries e dead-letter.
- Sentinela de integrações externas: Supabase, Stripe, Meta, Google, Autentique, ClickUp, WhatsApp.
- Alertas para falhas críticas, tokens expirados, webhooks quebrados e ingestão atrasada.
- QA auditor futuro para links, UTMs, criativos e entregas antes de publicar.

## 4. Fora de Escopo

- Construir APM próprio se ferramenta externa resolver melhor.
- Expor logs internos sensíveis ao cliente.
- Monitorar infraestrutura de terceiros que não temos como consultar.
- Fazer resposta automática destrutiva a incidentes.

## 5. Requisitos Funcionais

- RF1 — Sistema deve expor health endpoint da aplicação.
- RF2 — Sistema deve verificar conexão com Postgres, Redis, storage e workers.
- RF3 — Sistema deve capturar erros frontend/backend com contexto mínimo.
- RF4 — Jobs devem emitir status: queued, running, success, failed, retrying, dead-letter.
- RF5 — Integrações críticas devem ter status conhecido ou `unknown`, nunca silêncio.
- RF6 — Incidentes críticos devem gerar alerta para canal definido.
- RF7 — Status page deve mostrar estado resumido para componentes públicos.
- RF8 — Logs devem incluir correlation id para rastrear fluxo ponta a ponta.
- RF9 — Falha de token/credencial deve acionar dono operacional sem expor segredo.

## 6. Requisitos Não-Funcionais

- **Segurança:** logs não podem conter tokens, senhas, PII desnecessária ou prompts sensíveis.
- **Confiabilidade:** alertas críticos devem ter deduplicação para evitar spam.
- **Retenção:** logs e eventos precisam de política de retenção por criticidade.
- **Performance:** observabilidade não pode degradar fluxo principal perceptivelmente.
- **Operação:** incidentes devem ter severidade e owner.

## 7. Critérios de Aceite

- CA1 — Health check falha se banco ou Redis estiver indisponível.
- CA2 — Erro não tratado no frontend aparece na ferramenta de crash reporting.
- CA3 — Job que falha repetidamente entra em dead-letter e gera alerta.
- CA4 — Token expirado de integração aparece como incidente operacional.
- CA5 — Status page não vaza dados internos.
- CA6 — Um fluxo com erro pode ser rastreado por correlation id.

## 8. Riscos e Dependências

- **Risco:** excesso de alerta virar ruído.  
  **Mitigação:** severidade, deduplicação e owners.

- **Risco:** logar segredo por acidente.  
  **Mitigação:** redaction central e testes para campos sensíveis.

- **Dependência:** ADR Sentry/Datadog.
- **Dependência:** ADR BetterStack/Uptime/status page.
- **Dependência:** padronização de logs desde a fundação.

