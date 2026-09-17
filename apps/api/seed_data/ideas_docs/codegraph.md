# Adoção do CodeGraph

**Id:** codegraph
**Categoria:** Infra

## O que é
Integração de uma camada semântica de busca sobre o repositório para acelerar drasticamente a leitura e auditoria pelo Arquiteto ou Engenheiros IA.

## Detalhe da Absorção
Em vez do Arquiteto gastar tokens e tempo lendo arquivos crus na base do grep/glob, o CodeGraph indexa a AST (Abstract Syntax Tree) do repositório em um SQLite via tree-sitter. O Arquiteto faz queries diretas perguntando "Quais arquivos dependem da função X?", garantindo auditoria de código instantânea em projetos monolíticos.
