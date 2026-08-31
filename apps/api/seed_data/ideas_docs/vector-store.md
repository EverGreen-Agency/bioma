# Vector store EG (pgvector)

**Id:** vector-store
**Categoria:** Infra

## O que é
O banco de dados relacional e vetorial onde toda a nossa memória de longo prazo é armazenada e indexada por significado semântico.

## Detalhe da Absorção
Construído sobre o PostgreSQL (pgvector). Armazena as propostas enviadas, os relatórios de Raio-X, transcrições e cases de sucesso. A função `rag_search(query, client_id)` garante isolamento para que o contexto de um cliente nunca vaze na geração de texto de outro.
