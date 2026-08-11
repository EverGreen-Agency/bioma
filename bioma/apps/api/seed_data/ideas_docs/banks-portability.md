# Portabilidade dos bancos (não ser refém do opensquad)

**Id:** banks-portability
**Categoria:** Infra

## O que é
A decisão arquitetural de não "casar" nossos dados e inteligência proprietária com o framework subjacente (Opensquad ou qualquer outro).

## Detalhe da Absorção
Nossos bancos (Ideias, Stack, Arquitetura) devem permanecer sendo arquivos JSON/MD puramente portáveis e legíveis, talvez mudando do diretório interno `_opensquad/` para um top-level como `data/`. Mantemos o paradigma de usar arquivos em vez de Banco de Dados pesado (SQL) para facilitar a leitura crua por LLMs e o versionamento em Git.
