# Spec: mod-saas-billing

- **Cliente:** EverGreen + futuros clientes SaaS/white-label (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-saas-billing`, `reseller-revenda-depth`, `marketplace-addons`, `nome-plataforma`

## 1. Objetivo

Gerenciar planos, cobranças, assinaturas, entitlements, cotas, cupons, clientes legado, suspensão contratual e monetização white-label do Bioma.

## 2. Contexto

No início, a EG vende serviço premium e usa o Bioma como moat operacional. Em fases posteriores, clientes podem continuar pagando pela plataforma, parceiros podem operar white-label e módulos podem ser vendidos como add-ons. Isso exige billing limpo e suspensão legítima de acesso, nunca backdoor.

## 3. Escopo

O que será construído:

- Catálogo de planos, módulos, add-ons e entitlements.
- Integração com gateway de pagamento por ADR.
- Customers, subscriptions, invoices, status e webhooks.
- Regras de cotas: usuários, tenants filhos, módulos, IA, storage, dashboards.
- Cupons, ofertas especiais e clientes legado.
- Dunning/cobrança e suspensão contratual de acesso.
- Profundidade de revenda/reseller limitada por regra explícita.
- Sincronização financeira com `mod-financeiro`.

## 4. Fora de Escopo

- Cobrança SaaS antes de haver produto vendável.
- Backdoor, script nocivo ou travamento ilegítimo.
- Marketplace público completo no MVP.
- Split financeiro complexo para parceiros no início.
- Revenda infinita agência->agência->agência sem limite.

## 5. Requisitos Funcionais

- RF1 — Sistema deve cadastrar planos, módulos e limites.
- RF2 — Tenant deve possuir entitlements ativos/inativos por contrato/plano.
- RF3 — Webhook de pagamento deve atualizar status de assinatura.
- RF4 — Falha de pagamento deve iniciar régua de cobrança configurável.
- RF5 — Suspensão deve bloquear acesso de forma reversível e auditada.
- RF6 — Cliente legado deve poder ter plano/preço especial.
- RF7 — Reseller deve ter limite de subclientes e profundidade de revenda.
- RF8 — Add-on comprado deve liberar módulo/feature correspondente.
- RF9 — Eventos financeiros devem alimentar `mod-financeiro`.

## 6. Requisitos Não-Funcionais

- **Segurança:** billing não pode ser fonte de bypass de acesso.
- **Auditoria:** mudança de plano, suspensão e reativação precisam de log.
- **Resiliência:** webhooks idempotentes e reconciliáveis.
- **Compliance:** nota fiscal/tributos dependem de integração fiscal aprovada.
- **UX:** suspensão mostra banner claro, sem hostilidade.

## 7. Critérios de Aceite

- CA1 — Tenant sem entitlement não acessa módulo pago.
- CA2 — Pagamento confirmado libera acesso sem intervenção manual.
- CA3 — Falha de pagamento inicia dunning e não apaga dados.
- CA4 — Suspensão bloqueia acesso e reativação restaura sem perda.
- CA5 — Reseller não consegue criar subcliente acima do limite.
- CA6 — Cliente legado mantém preço/regra específica.

## 8. Riscos e Dependências

- **Risco:** escolher Stripe e faltar Pix/boleto/conciliação BR.  
  **Mitigação:** ADR gateway global-vs-BR.

- **Risco:** entitlements espalhados em ifs no frontend.  
  **Mitigação:** service catalog central e checagem server-side.

- **Dependência:** `mod-multitenant` para tenants/orgs.
- **Dependência:** `mod-financeiro` para DRE/receitas.
- **Dependência:** ADR gateway de pagamento.
- **Dependência:** ADR profundidade de revenda.

