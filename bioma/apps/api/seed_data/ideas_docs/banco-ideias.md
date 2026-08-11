# Banco de Ideias

**Id:** banco-ideias
**Categoria:** Cockpit

## O que é
É a fundação de gestão de roadmap de IA da EG. Onde novas ferramentas, squads e integrações são mapeadas e triadas (intake, dedup e conexão) pelo Curador, criando a fila oficial de engenharia.

## Detalhe da Absorção
O banco vive no JSON `ideas.json` e é gerido pelo squad `eg_banco_ideias`. A interação não é feita diretamente no código, mas pela tela do Cockpit no dashboard que renderiza a view `ideas.md` e o painel Kanban, permitindo visualizar as dependências e o status do portfólio.
