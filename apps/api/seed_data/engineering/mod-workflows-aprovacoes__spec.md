# Spec: mod-workflows-aprovacoes

- **Cliente:** EverGreen + clientes EG (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideia:** proposta de módulo transversal; registra e generaliza `tag-ativacao`

## 1. Objetivo

Criar um motor transversal de aprovações humanas para ações sensíveis do Bioma: publicar, enviar, cobrar, suspender, executar squad, alterar verba, revelar segredo ou liberar módulo.

## 2. Contexto

O projeto inteiro depende de HITL. Hoje essa lógica aparece como `tag-ativacao`, aprovações no client-hub, aprovar criativos, publicar case, enviar contrato, executar squad e liberar automação. Sem motor comum, cada módulo criará sua própria aprovação.

## 3. Escopo

O que será construído:

- Modelo único de approval request.
- Estados: draft, pending, approved, rejected, expired, cancelled, executed.
- Aprovação por papel, usuário, grupo ou tenant.
- Contexto rico: ação, risco, diff, destino, módulo, payload resumido.
- Assinatura/auditoria de decisão.
- Integração com cockpit interno e client-hub quando aprovação for do cliente.
- Policy de ações que sempre exigem aprovação.

## 4. Fora de Escopo

- Substituir sistema jurídico de assinatura.
- Permitir autoaprovação de ações críticas.
- Executar ações destrutivas sem reversibilidade declarada.
- Construir BPM complexo no MVP.

## 5. Requisitos Funcionais

- RF1 — Módulo deve criar pedido de aprovação com ação e contexto.
- RF2 — Aprovador deve ver risco, origem, destino e consequência.
- RF3 — Decisão deve registrar usuário, timestamp, comentário e resultado.
- RF4 — Pedido aprovado deve emitir evento para execução controlada.
- RF5 — Pedido rejeitado deve registrar motivo e bloquear execução.
- RF6 — Pedidos expirados não podem ser executados.
- RF7 — Sistema deve suportar aprovação interna EG e aprovação de cliente.
- RF8 — Ações sensíveis devem exigir approval policy server-side.

## 6. Requisitos Não-Funcionais

- **Auditabilidade:** trilha de aprovação não pode ser apagada.
- **Segurança:** aprovação no frontend não basta; enforcement no backend.
- **UX:** caixa de entrada clara, sem esconder risco.
- **Operação:** evitar excesso de aprovações triviais.

## 7. Critérios de Aceite

- CA1 — Uma ação sensível não executa sem aprovação válida.
- CA2 — Pedido aprovado dispara evento rastreável.
- CA3 — Pedido expirado não executa mesmo com link antigo.
- CA4 — Aprovação mostra diff/contexto suficiente para decisão.
- CA5 — Cliente só aprova itens do próprio tenant.

## 8. Riscos e Dependências

- **Risco:** burocracia travar operação.  
  **Mitigação:** classificar risco e exigir aprovação só onde importa.

- **Risco:** bypass por chamada direta de API.  
  **Mitigação:** policy server-side e testes de autorização.

- **Dependência:** `mod-cockpit-interno`.
- **Dependência:** `client-hub`.
- **Dependência:** `mod-multitenant`.

