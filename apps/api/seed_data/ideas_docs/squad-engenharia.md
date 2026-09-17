# Squad de Engenharia (SDD + ADR)

**Id:** squad-engenharia
**Categoria:** Squad

## O que é
A pipeline autônoma que transforma um Brief aprovado de cliente num repositório estruturado, passando por todas as etapas de design de software antes do código.

## Detalhe da Absorção
Workflow: Lê o Brief → Gera o Software Design Document (SDD) detalhando a solução → Documenta o porquê de cada decisão técnica nas ADRs → Realiza o scaffold do repositório inicial → Aciona sub-agentes para preencher os arquivos de código baseados nas tasks definidas. Mantém a sanidade de código nos entregáveis da agência.
