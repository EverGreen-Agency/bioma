# Spec: mod-radar-pesquisa

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-radar-pesquisa`, `tech-scout`, `mod-policy-research`, `squad-negocios`, `proveniencia-skills-mcp`, `absorver-opensource`

## 1. Objetivo

Criar a camada de pesquisa, radar, avaliação e proveniência que alimenta decisões técnicas, comerciais, políticas de plataforma, ferramentas externas, open-source e oportunidades de negócio.

## 2. Contexto

A EG quer operar com vantagem tecnológica, mas sem adotar ferramenta nova por hype. O radar precisa separar descoberta, avaliação, prova, decisão e adoção. Também precisa registrar origem de skills/MCPs e oportunidades de absorver open-source.

## 3. Escopo

O que será construído:

- Registro de pesquisas técnicas, ferramentas, políticas, APIs e oportunidades.
- Proveniência de skills, MCPs, prompts e referências.
- Avaliação build-vs-buy-vs-absorver.
- Radar de mudanças em políticas Meta/Google/WhatsApp e plataformas críticas.
- Fila de ferramentas para Tech Radar/Banco de Stack.
- Insumos para ADRs e Avaliador de Negócios.
- Pesquisa de open-source self-hosted reaproveitável.

## 4. Fora de Escopo

- Adotar ferramenta automaticamente.
- Fazer scraping proibido.
- Virar ferramenta acadêmica genérica.
- Substituir o Banco de Stack; este módulo alimenta e justifica.

## 5. Requisitos Funcionais

- RF1 — Sistema deve registrar item pesquisado com fonte, data, hipótese e owner.
- RF2 — Pesquisa deve gerar veredito: descartar, acompanhar, testar, adotar, comprar, absorver.
- RF3 — Skill/MCP deve registrar origem e licença/referência.
- RF4 — Mudança de política crítica deve gerar alerta para módulos afetados.
- RF5 — Ferramenta aprovada deve propor entrada/alteração no Banco de Stack.
- RF6 — Pesquisa usada em ADR deve ficar referenciada.
- RF7 — Open-source avaliado deve ter riscos de licença, segurança e manutenção.

## 6. Requisitos Não-Funcionais

- **Rastreabilidade:** toda recomendação precisa de fonte.
- **Atualidade:** pesquisas temporais precisam de data e validade.
- **Governança:** adoção final continua HITL/ADR.
- **Segurança:** avaliação de open-source inclui risco de supply chain.

## 7. Critérios de Aceite

- CA1 — Uma ferramenta pesquisada tem fonte, veredito e próxima ação.
- CA2 — Um ADR referencia pesquisa e ferramenta no radar.
- CA3 — Skill/MCP sem proveniência aparece como pendência.
- CA4 — Mudança crítica de API/política abre alerta.
- CA5 — Open-source avaliado tem licença e riscos registrados.

## 8. Riscos e Dependências

- **Risco:** pesquisar demais e executar de menos.  
  **Mitigação:** cada pesquisa precisa de decisão ou descarte.

- **Risco:** fonte desatualizada orientar decisão errada.  
  **Mitigação:** validade temporal e revisão periódica.

- **Dependência:** `mod-cockpit-interno`.
- **Dependência:** Banco de Stack.
- **Dependência:** `mod-observabilidade` para alertas de terceiros.

