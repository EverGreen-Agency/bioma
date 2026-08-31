# Spec: cofre-senhas

- **Cliente:** EverGreen + clientes EG (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** em execução — primeira vertical slice implementada, smoke runtime pendente
- **Versão:** 1.1
- **Ideias relacionadas:** `cofre-senhas`, `access-request-portal`, `mod-integrations-hub`, `mod-comercial`, `client-hub`

## 1. Objetivo

Substituir a prática atual de planilhas com usuário/senha por um cofre seguro, auditável e integrado ao onboarding de clientes e funcionários.

## 2. Contexto

Hoje acessos de cliente podem ficar em planilha com senha e usuário das plataformas. Isso é um risco operacional e jurídico: qualquer pessoa com acesso à planilha pode visualizar credenciais sensíveis, não há trilha confiável de quem viu/copiu e offboarding vira manual.

### Estado da implementação — 2026-07-22

A primeira vertical slice está em `bioma/`: migration 0021, API router/service/repository, tela `/clientes/:id/acessos` e `smoke_vault.py`. Ela cobre cifra obrigatória, metadados sem segredo, depósito pelo cliente, gestão por operador, revelação somente por administradores/workspace manager, motivo e auditoria. Aplicação da migration e smoke contra Postgres continuam pendentes; checklist de onboarding/offboarding, solicitação estruturada e decisão build-vs-buy antes de produção permanecem no backlog.

## 3. Escopo

O que será construído:

- Cadastro de credenciais por tenant, plataforma, conta e owner.
- Armazenamento criptografado de usuário, senha, token, recovery codes e notas sensíveis.
- Permissões por papel e por cliente.
- Log de visualização, cópia, edição, rotação e revogação.
- Checklist de onboarding de acessos: Google Ads MCC, Meta BM, Google Meu Negócio, Drive, Kommo, Autentique, WhatsApp, etc.
- Portal de solicitação de acessos para substituir planilhas com usuário/senha.
- Checklist de offboarding/rotação.
- Solicitação segura de acesso ao cliente, evitando planilha.
- Integração com `mod-integrations-hub` para conexões OAuth/API.

## 4. Fora de Escopo

- Construir um NordPass completo no MVP.
- Guardar segredo em JSON/git, logs ou campos não criptografados.
- Compartilhar senha por e-mail/WhatsApp automaticamente.
- Criar acesso a plataformas de cliente sem consentimento.
- Gerenciar chaves de produção da infraestrutura sem ADR específico de secrets management.

## 5. Requisitos Funcionais

- RF1 — Usuário autorizado deve cadastrar credencial vinculada a tenant e plataforma.
- RF2 — Credencial deve ter campos criptografados e metadados não sensíveis.
- RF3 — Usuário só pode revelar/copiar segredo com permissão explícita.
- RF4 — Toda revelação/cópia/edição deve gerar audit log.
- RF5 — Sistema deve permitir marcar credencial como expirada, comprometida, revogada ou em rotação.
- RF6 — Onboarding deve listar acessos pendentes por cliente.
- RF7 — Offboarding deve gerar tarefas de remoção/rotação.
- RF8 — Integrações OAuth devem referenciar segredo sem expor valor ao frontend.
- RF9 — Cliente deve conseguir cumprir solicitações de acesso por fluxo guiado, com fallback manual seguro.

## 6. Requisitos Não-Funcionais

- **Segurança:** criptografia forte em repouso; segredo nunca retorna em listagens.
- **Auditoria:** log imutável de acesso a segredo.
- **LGPD:** consentimento e finalidade por acesso sensível.
- **UX:** rápido o suficiente para substituir planilha, sem fricção excessiva.
- **Operação:** fallback manual seguro enquanto integrações OAuth não existem.

## 7. Critérios de Aceite

- CA1 — Credencial cadastrada não aparece em texto claro no banco, logs ou payload de listagem.
- CA2 — Usuário sem permissão não consegue revelar senha por UI nem API.
- CA3 — Revelar/copiar segredo gera log com usuário, tenant, horário e motivo.
- CA4 — Onboarding de cliente mostra acessos pendentes e concluídos.
- CA5 — Offboarding gera lista de credenciais a rotacionar/remover.
- CA6 — Uma credencial comprometida pode ser revogada e ocultada de uso.

## 8. Riscos e Dependências

- **Risco:** construir cofre próprio com segurança insuficiente.  
  **Mitigação:** ADR build-vs-buy vault antes de produção; começar pequeno e auditável.

- **Risco:** equipe continuar usando planilha por conveniência.  
  **Mitigação:** UX simples e onboarding obrigatório pelo cofre.

- **Dependência:** `mod-multitenant` para RBAC/RLS.
- **Dependência:** `mod-lgpd-governanca-dados` para consentimento/retenção.
- **Dependência:** ADR de criptografia/secrets management.
