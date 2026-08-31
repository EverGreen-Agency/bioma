# Spec: mod-contratos

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-contratos`, `mod-juridico`, `mod-financeiro`, `mod-comercial`

## 1. Objetivo

Automatizar o ciclo de vida de contratos da EG: geração a partir do deal, envio para assinatura, acompanhamento, eventos de assinatura e conexão com financeiro, onboarding e área do cliente.

## 2. Contexto

A EG já usa Autentique. O ganho inicial não é substituir assinatura digital, mas reduzir cópia manual, erro de dados, atraso de checagem e falta de ligação entre contrato, escopo vendido, cobrança, entregáveis e onboarding.

## 3. Escopo

O que será construído:

- Templates contratuais versionados e aprovados juridicamente.
- Geração de contrato a partir de dados do `mod-comercial`.
- Envio via Autentique API no MVP.
- Webhook de status: enviado, visualizado, assinado, recusado, expirado, cancelado.
- Registro de vigência, escopo, valores, parcelas, obrigações e anexos.
- Disparo de eventos para onboarding, financeiro e client-hub.
- Preparação para `mod-juridico`: validação de riscos, cláusulas e cumprimento de entregáveis.

## 4. Fora de Escopo

- Substituir Autentique no MVP.
- Gerar contrato jurídico sem template aprovado.
- Dar aconselhamento jurídico automático sem revisão humana.
- Alterar contrato assinado retroativamente.
- Fazer cobrança completa; isso pertence ao financeiro/billing.

## 5. Requisitos Funcionais

- RF1 — Sistema deve gerar contrato a partir de deal aprovado.
- RF2 — Contrato deve referenciar cliente, tenant, escopo, valores, vigência e responsáveis.
- RF3 — Template deve ter versão e status de aprovação.
- RF4 — Sistema deve enviar documento para assinatura via Autentique.
- RF5 — Sistema deve receber webhooks de assinatura e atualizar status interno.
- RF6 — Assinatura concluída deve acionar onboarding e financeiro.
- RF7 — Sistema deve guardar evidências: documento, hash/ID externo, timestamps e signatários.
- RF8 — Alterações manuais em contrato devem exigir justificativa e auditoria.
- RF9 — Sistema deve sinalizar contrato vencendo, vencido ou pendente.

## 6. Requisitos Não-Funcionais

- **Segurança:** contratos restritos por papel; URLs/documentos com acesso controlado.
- **Confiabilidade:** webhook idempotente; não duplicar eventos de assinatura.
- **Auditoria:** cada status relevante precisa de histórico.
- **Jurídico:** templates só entram em produção com aprovação humana.
- **Privacidade:** contratos não podem aparecer no client-hub sem permissão explícita.

## 7. Critérios de Aceite

- CA1 — Um deal `Closed Won` gera contrato a partir de template aprovado.
- CA2 — Webhook `document.signed` altera status uma única vez e dispara eventos corretos.
- CA3 — Contrato assinado aciona financeiro para setup/faturamento e onboarding para ativação.
- CA4 — Usuário sem permissão não baixa contrato de cliente.
- CA5 — Um contrato vencendo aparece em alerta operacional.
- CA6 — A versão do template usado fica preservada no contrato.

## 8. Riscos e Dependências

- **Risco:** contrato gerado com escopo/valor errado por dados comerciais incompletos.  
  **Mitigação:** checklist e aprovação antes de envio.

- **Risco:** webhook externo falhar e onboarding não iniciar.  
  **Mitigação:** reconciliação periódica com Autentique.

- **Dependência:** `mod-comercial` para dados de deal.
- **Dependência:** `mod-financeiro` para cobrança/NF.
- **Dependência:** `mod-juridico` para validação futura.
- **Dependência:** ADR Autentique manter-vs-absorver.

