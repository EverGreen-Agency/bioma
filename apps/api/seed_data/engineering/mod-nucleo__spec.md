# Spec: mod-nucleo

- **Cliente:** EverGreen + plataforma Bioma (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-nucleo`, `mod-multitenant`, `cofre-senhas`, `mod-integrations-hub`, `mod-workflows-aprovacoes`, `mod-lgpd-governanca-dados`

## 1. Objetivo

Agrupar as capacidades fundacionais do Bioma que todos os módulos herdam: tenancy, auth, RBAC, auditoria, integrações, vault, aprovações, governança de dados e entitlements básicos.

## 2. Contexto

`mod-multitenant` começou a produção e cobre a base de auth/tenant/RLS. Ainda assim, o núcleo da plataforma é maior que multi-tenant: ele inclui as proteções e contratos transversais que impedem os módulos de criarem soluções isoladas e inseguras.

## 3. Escopo

- Consolidar decisões transversais de fundação.
- Definir contratos comuns de usuário, organização, tenant, papel, permissão, auditoria e entitlement.
- Orquestrar dependências entre multitenant, cofre, integrações, workflows e LGPD.
- Definir padrões obrigatórios para novos módulos.

## 4. Fora de Escopo

- Virar módulo de tela próprio no MVP.
- Implementar regra específica de negócio de cada domínio.
- Substituir specs dos módulos fundacionais individuais.

## 5. Requisitos Funcionais

- RF1 — Todo módulo deve declarar como usa tenant, RBAC e auditoria.
- RF2 — Todo acesso a segredo deve passar pelo cofre.
- RF3 — Toda integração externa deve passar pelo hub de integrações.
- RF4 — Toda ação sensível deve declarar se exige aprovação.
- RF5 — Todo dado sensível deve ter classificação.

## 6. Requisitos Não-Funcionais

- **Consistência:** contratos transversais iguais para todos os módulos.
- **Segurança:** núcleo prioriza prevenção de vazamento cross-tenant.
- **Evolução:** módulos podem nascer simples, mas sem bypass da fundação.

## 7. Critérios de Aceite

- CA1 — Nova spec de módulo informa dependências do núcleo.
- CA2 — Módulo não acessa segredo diretamente.
- CA3 — Módulo não cria integração externa fora do hub.
- CA4 — Ação sensível sem aprovação declarada é apontada na revisão.

## 8. Riscos e Dependências

- **Risco:** o núcleo virar abstração grande demais.  
  **Mitigação:** manter como conjunto de contratos e specs, não como mega-framework.

- **Dependência:** `mod-multitenant`.
- **Dependência:** ADRs transversais.

