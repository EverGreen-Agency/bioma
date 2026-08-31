# Spec: mod-financeiro

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-financeiro`, `ai-credits-metering`, `planejamento-negocios`, `micro-aws-hosting`, `mod-saas-billing`

## 1. Objetivo

Centralizar previsibilidade financeira, viabilidade de investimentos, cobranças, inadimplência, custos operacionais e uso de créditos de IA da EverGreen.

## 2. Contexto

A EG tem planilhas pessoais/corporativas como referência, mas o Bioma precisa separar dados pessoais de dados da empresa. O módulo financeiro nasce para apoiar decisões pragmáticas: contratar, assinar ferramenta, construir módulo, manter cliente, cobrar, investir ou adiar.

## 3. Escopo

O que será construído:

- Cadastro de receitas, custos, despesas, centros de custo e projetos.
- Forecasting de caixa, MRR, setup, contratos recorrentes e cenários.
- Simulação de viabilidade para módulos, ferramentas e contratações.
- Controle de inadimplência e status de cobrança por cliente.
- Visão de custos por cliente, operação e squad quando houver dados.
- Medição de créditos de IA por modelo, provedor, escopo e tenant.
- Integração com billing, contratos e contábil/fiscal por ADR.
- Alertas de custo anômalo, limite de IA e risco de caixa.

## 4. Fora de Escopo

- Misturar Fóton/finanças pessoais com financeiro EG.
- Substituir contador ou responsabilidade fiscal sem validação.
- Emitir NFS-e sem ADR e integração homologada.
- Fazer trading/investimentos autônomos dentro da EG.
- Expor margem ou caixa para clientes.

## 5. Requisitos Funcionais

- RF1 — Sistema deve registrar receitas e despesas por categoria, projeto, cliente e competência.
- RF2 — Sistema deve calcular forecast mensal e cenários de contratação/investimento.
- RF3 — Sistema deve listar clientes inadimplentes e ações de cobrança.
- RF4 — Sistema deve receber eventos de contrato assinado e pagamento/falha de billing.
- RF5 — Sistema deve medir uso de IA por provedor/modelo, tenant, usuário, módulo e origem (API/CLI/subscription quando rastreável).
- RF6 — Sistema deve alertar estouro de orçamento, custo anômalo ou limite de crédito.
- RF7 — Sistema deve simular payback/ROI de ferramentas ou módulos antes de adoção.
- RF8 — Sistema deve exportar dados para contabilidade quando integração não estiver pronta.

## 6. Requisitos Não-Funcionais

- **Segurança:** acesso restrito a `financeiro_admin` e papéis aprovados.
- **Precisão:** valores monetários em centavos ou decimal; nunca float para cálculo financeiro.
- **Auditoria:** alterações em valor, status de cobrança e centro de custo devem ser auditadas.
- **Privacidade:** margem, folha e custos internos não aparecem em áreas de cliente.
- **Resiliência:** integração bancária/fiscal deve ter fallback manual.

## 7. Critérios de Aceite

- CA1 — Usuário sem papel financeiro não consegue acessar dados de caixa/custo.
- CA2 — Uma despesa e uma receita recorrente entram no forecast mensal.
- CA3 — Um cliente inadimplente aparece com status, valor, contrato e próxima ação.
- CA4 — Uso de IA é registrado por pelo menos módulo, usuário e provedor/modelo quando disponível.
- CA5 — Cálculos financeiros não apresentam erro de ponto flutuante em centavos.
- CA6 — Uma simulação de assinatura de ferramenta mostra custo mensal, dono e justificativa.

## 8. Riscos e Dependências

- **Risco:** criar ERP antes de ter operação suficiente.  
  **Mitigação:** começar com forecast, cobranças, custos e créditos de IA.

- **Risco:** dados financeiros pessoais contaminarem dados EG.  
  **Mitigação:** Fóton separado; importar apenas lógica, não dados pessoais.

- **Dependência:** `mod-saas-billing` para assinaturas.
- **Dependência:** `mod-contratos` para valores e vigência.
- **Dependência:** ADR integração bancária/contábil.
- **Dependência:** ADR créditos de IA/metering.

