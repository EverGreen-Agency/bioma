# eg-mcp-tools (MCP padronizado)

**Id:** eg-mcp-tools
**Categoria:** Infra

## O que é
A nossa própria coleção de Model Context Protocol (MCP) servers para interagir com o ecossistema SaaS da agência de forma segura.

## Detalhe da Absorção
Desenvolvimento de servidores MCP como o `clickup_writer`, `kommo_writer`, `ga4_reader`. Fundamental: eles possuem annotations rígidos de risco — `Write/Read barrier` — garantindo que os agentes não tenham permissão silenciosa de apagar coisas do CRM ou publicar sem aprovação humana.
