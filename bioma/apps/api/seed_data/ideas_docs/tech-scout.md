# Tech Scout — radar de ferramentas

**Id:** tech-scout
**Categoria:** Squad

## O que é
Vigília proativa (outbound) do ecossistema tech: garimpa onde a comunidade de devs é ativa — YouTube, Reddit, X, Hacker News, GitHub trending — por MCPs, APIs, ferramentas, frameworks e papers aplicáveis que valham entrar no radar da EG.

## Por que existe (e o que NÃO é)
É o complemento do Arquiteto, não substituto:
- **Arquiteto** = inbound/reativo: "pra ESTA necessidade, o que já temos / integramos / assinamos / construímos?".
- **Tech Scout** = outbound/proativo: "surgiu isso novo lá fora — vale um lugar no Tech Radar?".

## Como funciona
1. Varre as fontes (reaproveita a máquina do Sherlock, que já lê YouTube/X via browser — muda só o assunto: ferramenta tech, não perfil de conteúdo).
2. Filtra pelo que é relevante ao stack/roadmap da EG (cruza com `stack.json` e `ideas.json` pra não trazer o que já temos/descartamos).
3. **Propõe** entradas no Banco de Stack (anel Assess) e/ou no Banco de Ideias — sempre HITL. Nunca adota nem assina sozinho.

## Conexões
- **Habilita** `banco-stack` (alimenta o Tech Radar com candidatos).
- Parente de `eg-mcp-tools` (o que ele acha pode virar tool nossa) e `codegraph` (ferramentas de indexação são candidatas típicas).
- Reusa a infra do Sherlock (`_opensquad/core/prompts/sherlock-*`).
