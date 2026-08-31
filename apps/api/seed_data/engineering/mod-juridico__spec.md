# Spec: mod-juridico

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-juridico`, `mod-contratos`, `mod-lgpd-governanca-dados`

## 1. Objetivo

Apoiar a EG na revisão de riscos jurídicos, aderência de contratos, mudanças legais relevantes e cumprimento de entregáveis contratados.

## 2. Contexto

A parte 2 trouxe a necessidade de verificar se contratos continuam aderentes à lei, se entregáveis estão sendo cumpridos e se há fragilidade jurídica para EG ou clientes. Este módulo não substitui advogado; ele organiza inteligência e alertas.

## 3. Escopo

- Biblioteca de cláusulas, templates e riscos.
- Checklist de revisão jurídica por contrato.
- Monitoramento de obrigações e entregáveis contratados.
- Alertas de mudanças legais/políticas que afetam contratos.
- Parecer assistido por IA com revisão humana obrigatória.

## 4. Fora de Escopo

- Dar aconselhamento jurídico autônomo.
- Assinar ou alterar contrato sem humano.
- Monitorar todo ordenamento jurídico sem recorte.

## 5. Requisitos Funcionais

- RF1 — Contrato deve poder receber checklist jurídico.
- RF2 — Obrigações do contrato devem virar itens monitoráveis.
- RF3 — Mudança legal/política relevante deve gerar alerta.
- RF4 — Parecer de IA deve mostrar fontes e incertezas.
- RF5 — Revisão humana deve aprovar qualquer recomendação jurídica externa.

## 6. Requisitos Não-Funcionais

- **Rastreabilidade:** toda conclusão precisa de fonte/data.
- **Responsabilidade:** IA não decide; humano valida.
- **Privacidade:** contratos e dados jurídicos têm acesso restrito.

## 7. Critérios de Aceite

- CA1 — Um contrato tem obrigações extraídas e monitoráveis.
- CA2 — Parecer jurídico assistido mostra fonte e data.
- CA3 — Recomendação não aparece como aprovada sem revisão humana.
- CA4 — Usuário sem permissão não acessa contrato/parecer.

## 8. Riscos e Dependências

- **Risco:** alucinação jurídica.  
  **Mitigação:** fontes, revisão humana e escopo restrito.

- **Dependência:** `mod-contratos`.
- **Dependência:** `mod-policy-research`.

