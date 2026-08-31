# Spec: mod-integrations-hub

- **Cliente:** EverGreen + clientes EG (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-integrations-hub`, `integration-doctor`

## 1. Objetivo

Centralizar o catálogo, autenticação, status e governança das integrações externas do Bioma: Meta, Google, LinkedIn, Autentique, ClickUp, Kommo, WhatsApp, Stripe, Drive, Google Meu Negócio e outras.

## 2. Contexto

As specs atuais citam integrações em vários lugares. Sem um hub transversal, cada módulo tende a reinventar OAuth, status, webhooks, tokens, retries e permissões. Isso aumenta risco de vazamento, duplicação e comportamento inconsistente.

## 3. Escopo

O que será construído:

- Catálogo de provedores externos e capacidades disponíveis.
- Conexões por tenant, conta, escopo, status e owner.
- Fluxos OAuth/API-key delegados ao `cofre-senhas`.
- Registro de permissões concedidas, expiração, health e última sincronização.
- Webhook registry e assinatura de eventos externos.
- Painel de status por integração e tenant.
- Adapter padrão para módulos consumirem integrações sem lidar com segredo diretamente.
- Integration Doctor: diagnóstico de causa, impacto e próxima ação para integrações quebradas.

## 4. Fora de Escopo

- Implementar todos os conectores no MVP.
- Guardar segredo em texto claro.
- Automatizar ações de escrita em plataformas externas sem HITL.
- Virar iPaaS genérico.

## 5. Requisitos Funcionais

- RF1 — Sistema deve cadastrar provedor e tipos de conexão suportados.
- RF2 — Tenant deve ter conexões com status: pendente, ativa, erro, expirada, revogada.
- RF3 — Módulos devem consultar status da integração por API interna.
- RF4 — Webhooks externos devem ser recebidos com idempotência e validação.
- RF5 — Sistema deve registrar escopos/permissões concedidos.
- RF6 — Falha recorrente deve abrir incidente em `mod-observabilidade`.
- RF7 — Conexão revogada deve bloquear jobs dependentes.
- RF8 — Sistema deve explicar falhas comuns em linguagem operacional: token expirado, webhook falhou, pixel sem evento, UTM quebrada, job atrasado.

## 6. Requisitos Não-Funcionais

- **Segurança:** módulo nunca expõe segredo para frontend.
- **Confiabilidade:** retries e backoff padronizados.
- **Auditabilidade:** conexão/criação/revogação precisa de log.
- **Extensibilidade:** adicionar provedor não deve exigir reescrever módulos consumidores.

## 7. Critérios de Aceite

- CA1 — Um tenant conecta uma plataforma e módulos conseguem consultar status.
- CA2 — Token expirado aparece como conexão expirada e bloqueia job dependente.
- CA3 — Webhook duplicado não duplica evento de negócio.
- CA4 — Usuário sem permissão não cria/revoga conexão.
- CA5 — Falha de integração aparece no painel operacional.

## 8. Riscos e Dependências

- **Risco:** virar abstração grande antes de haver conectores reais.  
  **Mitigação:** começar com conectores que bloqueiam Fase 1: Meta/Google/Auth/Autentique.

- **Dependência:** `cofre-senhas`.
- **Dependência:** `mod-observabilidade`.
- **Dependência:** ADR OAuth/API-key por provedor crítico.
