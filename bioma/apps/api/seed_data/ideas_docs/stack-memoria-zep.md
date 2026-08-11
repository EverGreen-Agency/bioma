# Segundo Cérebro — stack de memória (Zep)

**Id:** stack-memoria-zep
**Categoria:** Infra

## O que é
Integração de um banco de retenção longa específico para LLMs, como o Zep, atuando acima do Vector Store primitivo.

## Detalhe da Absorção
Fase 1.5 do RAG. Em vez de fazer buscas burras no pgvector, o Zep atua condensando e sumariando conversas passadas para manter o contexto dos clientes sempre rápido na memória curta dos agentes, otimizando o gasto de tokens e evitando esquecimento de detalhes cruciais.
