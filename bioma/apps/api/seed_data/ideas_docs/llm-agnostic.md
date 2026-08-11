# Camada LLM-agnostic

**Id:** llm-agnostic
**Categoria:** Infra

## O que é
A garantia de não sermos reféns da OpenAI ou da Anthropic. Toda a inteligência artificial do sistema passa por um roteador padronizado.

## Detalhe da Absorção
Utilizando um gateway (como LiteLLM ou OpenRouter), os agentes do Opensquad solicitam completions genéricas. Trocar o modelo base de todo o OS de GPT-4o para Claude 3.5 Sonnet é a mudança de uma única variável de ambiente.
