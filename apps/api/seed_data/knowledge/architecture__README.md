# Banco de Arquitetura EG

Guarda o **porquê** da estrutura da EverGreen — **identidade**, **princípios de engenharia** e **decisões arquiteturais**. É a referência de princípios do **Arquiteto** (squad `eg_arquiteto`) no gate de princípios.

**Não é mais um espelho do filesystem.** O inventário vivo — quais squads existem, qual stack, quais integrações — não mora aqui: o Arquiteto lê direto do repo (`squads/*/squad.yaml`, `stack.json`, `.mcp.json`, o código). Espelhar o filesystem num doc só cria divergência.

## Arquivos

- **`arquitetura.md`** — identidade + princípios + decisões (D1, D2, …). O "porquê".
- **`README.md`** — este arquivo.

## Diferença para o Banco de Ideias

| | Banco de Ideias | Banco de Arquitetura |
|---|---|---|
| Pergunta | "o que queremos construir?" | "por que a estrutura é assim?" |
| Conteúdo | visão, desejos, futuro | princípios e decisões firmadas |
| Dono | Curador (`eg_banco_ideias`) | Arquiteto (`eg_arquiteto`) |

## Como mexer

- **Princípios e decisões:** edite `arquitetura.md` quando uma escolha estrutural se firma. Documento curto e estável de propósito.
- **Via Arquiteto:** ao auditar, ele pode propor uma decisão nova (D-x) — mas só grava com aprovação humana (Write/Read barrier).
- **Inventário (quais squads/techs/integrações):** não se edita aqui. Mexa no próprio repo (crie o squad, edite o `stack.json`) — o Arquiteto e o dashboard leem ao vivo.

## Por que existe

Há coisas que o código não conta: *por que* o framework é Markdown/YAML e não código, *por que* os bancos são JSON e não um BD, *por que* Curador e Arquiteto são separados. Esse é o conhecimento que envelheceria se não fosse escrito — e que dá ao Arquiteto o chão para o gate de princípios. O "o quê existe" ele lê do repo; o "por que é assim" lê daqui.
