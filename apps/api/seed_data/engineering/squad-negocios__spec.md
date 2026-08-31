# Spec: squad-negocios

- **Cliente:** EverGreen/Quark, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho baixa prioridade
- **Versão:** 1.0
- **Ideias relacionadas:** `squad-negocios`, `planejamento-negocios`, `mod-radar-pesquisa`, `mod-financeiro`

## 1. Objetivo

Apoiar decisões de novas empresas, spin-offs, M&A, produtos paralelos e apostas estratégicas, usando dados financeiros, radar e avaliação de negócios.

## 2. Contexto

Eduardo trouxe visão de holding/ecossistema. Muitas ideias são separadas da Mega Plataforma, mas precisam de um lugar para análise: Fóton, Prisma BI, Telecom, Micro AWS, educação, jogos, trading, etc.

## 3. Escopo

- Registro de oportunidades de negócio.
- Avaliação por tese, ROI, risco, capital, tempo e sinergia.
- Separação entre core EG, spin-off e fora de escopo.
- Integração com financeiro para viabilidade.

## 4. Fora de Escopo

- Executar M&A real sem assessoria.
- Misturar dados pessoais/Fóton com EG.
- Aprovar investimento automaticamente.

## 5. Requisitos Funcionais

- RF1 — Ideia de negócio deve ter tese, dono, estágio e classificação.
- RF2 — Avaliação deve indicar construir, adiar, separar ou descartar.
- RF3 — Decisão deve registrar critérios e fontes.
- RF4 — Oportunidade pode gerar nova ideia/projeto fora do Bioma.

## 6. Requisitos Não-Funcionais

- **Governança:** decisões estratégicas sempre HITL.
- **Separação:** respeitar fronteira EG vs pessoal vs spin-off.
- **Rastreabilidade:** preservar por que a decisão foi tomada.

## 7. Critérios de Aceite

- CA1 — Uma ideia separada tem justificativa e destino.
- CA2 — Viabilidade financeira referencia dados/suposições.
- CA3 — Decisão não vira tarefa de engenharia sem aprovação.

## 8. Riscos e Dependências

- **Risco:** dispersar foco da EG.  
  **Mitigação:** classificar e estacionar ideias longas.

- **Dependência:** `mod-financeiro`.
- **Dependência:** `mod-radar-pesquisa`.

