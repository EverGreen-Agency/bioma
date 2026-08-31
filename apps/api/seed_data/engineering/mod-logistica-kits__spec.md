# Spec: mod-logistica-kits

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-logistica-kits`, `client-hub`, `gamificacao-setup`

## 1. Objetivo

Controlar inventário, montagem, personalização, provisionamento NFC e entrega dos kits físicos da EG para clientes e, futuramente, equipamentos de funcionários.

## 2. Contexto

O kit é uma peça de experiência premium e também um gateway físico para o client-hub via cartão NFC. Hoje esse controle tende a ficar manual: estoque, fornecedores, custos, personalização, expedição e status de entrega.

## 3. Escopo

O que será construído:

- Cadastro de itens do kit, fornecedores, custo, estoque e status.
- Modelos de kit por nível/oferta: setup, retainer, high-end, funcionário.
- Ordem de montagem por cliente/deal.
- Provisionamento de cartão NFC associado a tenant/magic link.
- Checklist de personalização: carta, roadmap, links e materiais.
- Status de expedição e entrega.
- Integração futura com Correios/Loggi.
- Registro de hardware comodato para funcionários em fase posterior.

## 4. Fora de Escopo

- Criar ERP de estoque completo.
- Comprar/emitir frete automaticamente no MVP.
- Monitorar cuidado do cliente com planta/souvenir.
- Usar NFC como autenticação permanente sem token seguro.
- Gerenciar cadeia de fornecedores complexa no início.

## 5. Requisitos Funcionais

- RF1 — Sistema deve cadastrar itens, quantidades, custo e fornecedor.
- RF2 — Sistema deve criar ordem de kit a partir de cliente/deal aprovado.
- RF3 — Sistema deve associar serial do cartão NFC a tenant e status.
- RF4 — Sistema deve registrar montagem, envio, rastreio e entrega.
- RF5 — Sistema deve alertar estoque baixo de itens críticos.
- RF6 — Sistema deve guardar quais clientes receberam quais kits e quando.
- RF7 — Sistema deve permitir revogar/reemitir link NFC em caso de perda.
- RF8 — Sistema deve enviar evento para `client-hub` quando kit for entregue.

## 6. Requisitos Não-Funcionais

- **Segurança:** NFC nunca aponta direto para segredo; apenas para fluxo controlado.
- **Operação:** processo simples, suficiente para baixo volume inicial.
- **Auditoria:** alterações em serial NFC e tenant devem ser logadas.
- **Financeiro:** custos devem poder alimentar `mod-financeiro`.

## 7. Critérios de Aceite

- CA1 — Um kit pode ser criado, montado, enviado e marcado como entregue.
- CA2 — Um cartão NFC fica vinculado a tenant e pode ser revogado.
- CA3 — Estoque reduz ao montar kit e alerta quando abaixo do mínimo.
- CA4 — Histórico mostra qual cliente recebeu qual versão de kit.
- CA5 — Link NFC expirado/revogado não permite acesso.

## 8. Riscos e Dependências

- **Risco:** sofisticar logística antes de volume justificar.  
  **Mitigação:** MVP manual assistido com estoque e NFC.

- **Risco:** cartão NFC virar vulnerabilidade.  
  **Mitigação:** magic link curto, revogação e auditoria.

- **Dependência:** `client-hub` para destino final.
- **Dependência:** `mod-multitenant` para tenant.
- **Dependência:** ADR NFC/magic link.

