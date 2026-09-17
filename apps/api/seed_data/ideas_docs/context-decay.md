# Context Decay

**Id:** context-decay
**Categoria:** Infra

## O que é
Um princípio matemático aplicado ao RAG (Retrieval-Augmented Generation) para esquecer informações obsoletas.

## Detalhe da Absorção
Toda entrada no Vector Store ganha um timestamp. Na hora da busca vetorial, o score de similaridade é multiplicado por um "peso de recência" (decay). Assim, metodologias antigas da agência são naturalmente substituídas pelas novas sem precisar que ninguém as delete.
