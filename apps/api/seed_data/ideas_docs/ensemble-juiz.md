# Ensemble + Juiz (Mixture of Agents)

**Id:** ensemble-juiz
**Categoria:** Infra

## O que é
Arquitetura de deliberação para tarefas críticas, usando múltiplos modelos menores competindo e um modelo grande julgando a melhor resposta.

## Detalhe da Absorção
Em cenários complexos (como fechar a arquitetura de um software de cliente no `squad-engenharia`), rodamos modelos baratos (ex: Llama 3) em paralelo (Ensemble) gerando várias propostas de solução. Um LLM premium atua como Juiz, lendo todas e sintetizando a decisão final. Aplicado apenas em etapas de alto ROI devido ao custo e latência.
