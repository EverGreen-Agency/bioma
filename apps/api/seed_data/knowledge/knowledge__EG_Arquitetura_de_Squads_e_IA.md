**EVERGREEN · EG**

# Arquitetura de Squads e IA

> **A constituição dos squads da EverGreen.** Guarda só o **atemporal**: princípios, o padrão de squad e os guardrails. O que muda com o tempo **não mora aqui** — o inventário vivo (stack, squads, integrações) lê-se das fontes reais, e o roadmap vive no Banco de Ideias. Complementa o **Documento Mestre** (posicionamento, oferta, operação).
>
> Atualizado: 2026-07-01.

## Onde mora cada coisa (pra este doc não apodrecer)

Este doc é referência estável — inclusive nos Projetos do Claude. Por isso ele **não** guarda inventário que envelhece; ele aponta pra fonte viva:

| O quê | Onde vive | Como se lê |
| :---- | :---- | :---- |
| Princípios, padrão de squad, guardrails | **aqui** | doc atemporal |
| Stack / Tech Radar (o que usamos, em que anel) | `_opensquad/_memory/banco_stack/stack.json` | lido ao vivo |
| Quais squads existem e o que fazem | `squads/` | lido ao vivo pelo Arquiteto — nunca uma lista à mão |
| Roadmap / o que construir / moonshots | Banco de Ideias (`_opensquad/_memory/banco_ideias/ideas.json`) | Curador |
| Integrações / MCPs ativos | `.mcp.json` | lido ao vivo |
| Decisões arquiteturais (o porquê) | `_opensquad/_memory/banco_arquitetura/arquitetura.md` | Arquiteto |

## 0. Princípios fundamentais (a constituição dos squads)

Antes de qualquer ferramenta, cinco princípios que não se quebram:

1. **Squad é por função, não por cliente.** Um squad resolve um *tipo de problema* (prospecção, proposta, conteúdo, relatório). O cliente é uma *configuração* injetada em tempo de execução — nunca um repositório novo. Squad por cliente = 20 repositórios duplicados e manutenção impossível em 6 meses.

2. **Cliente é configuração, não arquitetura.** Voz, tom, regras de negócio, chaves de API e contexto de cada cliente vivem em arquivos de configuração (JSON/banco), carregados por ID. O código do squad é o mesmo para todos.

3. **Autonomia proporcional ao raio de impacto — não ao tipo de squad.** O quanto um agente age sozinho é definido pelo *impacto de um erro daquela ação*, não por quem o squad serve. Ação que toca sistema vivo de cliente (ads, CRM, e-mail) = autonomia mínima + HITL, sempre. Ação de baixo impacto (rascunho/leitura interna) = mais autonomia. Um **mesmo squad pode servir interno e cliente** via configuração (squad é por função — princípio #1); o que muda por execução são dois mostradores independentes: **autonomia** (pelo raio de impacto) e **isolamento** (contexto/chaves por `client_id`). "Interno × entrega" é atalho mental, não regra de fatiar squads.

4. **Código para dados, LLM para raciocínio.** Não escreva lógica complexa de if/else quando bastaria ajustar o prompt; e não tente resolver com prompt o que um código simples de manipulação de JSON resolve melhor. Automação são os trilhos; agentes são os nós cognitivos.

5. **Human-in-the-loop (HITL) é obrigatório em qualquer ação externa.** Nenhum agente dispara e-mail, mensagem, anúncio ou publicação sem aprovação humana. O output nasce como *rascunho* e um humano aprova.

## 1. Arquitetura atual: enxuta por escolha (motor antes de interface)

Hoje a EG roda **enxuto**: squads são `squad.yaml` + `.agent.md` interpretados pelo Claude Code (framework Opensquad) — versionáveis em git, sem build, sem runtime próprio a manter. Não é limitação; é a aplicação de dois princípios: **"motor antes de interface"** e **"começar barato, escalar só quando o enxuto parar de servir"**.

A "stack completa" (runtimes de agente, orquestrador de dados, RAG, infra dedicada) é **evolução com gatilho**, não o estado atual. Cada peça pesada entra quando um limite real aparece:

| Peça pesada | Gatilho para adotar |
| :---- | :---- |
| Orquestração de dados (ex.: n8n) | pipeline cruza 3+ sistemas simultâneos e a cola vira gargalo |
| Runtime de agentes determinístico (ex.: LangGraph) | squad de receita precisa de estado determinístico + auditoria dura |
| RAG (ex.: pgvector/Zep) | volume de conhecimento estoura o contexto da LLM (hoje cabe) |
| Infra dedicada | volume justifica custo fixo vs. serviços gerenciados |

> A stack concreta (ferramentas e anéis de adoção) **não é listada aqui** — vive no `stack.json`. **Regra de modelo:** mapeie por **capacidade** ("melhor de raciocínio", "melhor de contexto longo", "mais barato pra volume"), nunca por versão fixa — versões mudam a cada poucos meses; a lógica de *qual tipo pra qual tarefa* permanece.

### Service-as-a-Software: motor invisível, valor visível

Para o cliente, squads não são vendidos como "robôs". Eles são o motor de bastidor que permite à EG entregar com mais velocidade, padrão, margem e profundidade. A interface pública deve expor apenas o que aumenta confiança: score, status, evidências, aprovações, próximos passos e progresso.

A complexidade operacional dos agentes permanece interna, governada por HITL, logs e isolamento por `client_id`. A regra de produto é: valor visível para o cliente; complexidade técnica visível apenas para a operação EG.

### As 3 camadas de execução (sequenciamento)

| Camada | O que é | Status |
| :---- | :---- | :---- |
| **Squads (CLI/código)** | lógica pura, sem interface | ← onde estamos |
| **Cockpit interno** | interface: clientes, execução, logs, BI embutido | depois do motor |
| **Plataforma pública** | multi-tenant produtizado (a arquitetura stateless/cliente-por-ID já suporta) | escala de mercado |

Regra: **não construir interface antes de ter motor.** Cockpit vazio não vale nada; squad sem interface já vale.

## 2. Governança e guardrails

Autonomia é gate pelo **raio de impacto da ação** (princípio #3), não pelo tipo de squad. Os três riscos técnicos que mais ameaçam a EG:

1. **Vazamento de contexto (context bleeding):** mesma sessão/memória para dois clientes. → agentes *stateless*, contexto injetado por `client_id` a cada chamada.
2. **Loop fatal / autonomia não supervisionada:** agente em loop gera spam ou queima tokens numa madrugada. → `max_iterations` fixo, orçamento por API, HITL em qualquer gatilho externo.
3. **Complexidade excessiva:** misturar lógica de software com raciocínio de LLM no lugar errado. → código pro tráfego de dados, LLM pra raciocínio.

**Regra de dados/BI (durável):** relatórios e BI apontam para um store próprio da EG (normalizado por pipeline de dados), nunca para fonte manual nem para a plataforma da ad network direto. Trocar a ferramenta de BI vira re-skin; trocar o pipeline de dados, não.

## 3. Como estruturar um squad (o padrão)

**Um squad = um resultado (workflow). Dentro dele, vários agentes-papel.** Não se cria sub-squad por **plataforma** nem por **formato** — plataforma e formato são **parâmetros de configuração**.

Exemplo — Squad de Conteúdo: um só squad, com papéis internos (Estrategista, Roteirista de Gancho, de Corpo, de CTA, Editor/Voz da Marca, Repurposer). "Gere para LinkedIn, formato carrossel, voz X" entra como **input**, não como squad separado. Um squad que sabe fazer para várias plataformas > vários squads de uma plataforma cada. Especialização por plataforma só vale **depois**, com volume e padrão estabelecidos.

**Uso pessoal (ex.: social do Eduardo)** = o mesmo squad de conteúdo com uma *config* diferente (voz/tom/temas dele). Não cria arquitetura nova — cria um client config. Prova o princípio: pessoa/cliente = configuração.

**Quando squad vs. ferramenta direta:**
- **Ferramenta direta (curadoria humana):** peça artesanal, alta qualidade, baixo volume — design final, vídeo premium, imagem de marca. Use Claude Design, Figma, editores.
- **Squad:** repetível, alto volume, baixa variância — 50 variações de copy, 100 leads, 20 relatórios.
- Regra: qualidade/unicidade → humano + ferramenta; escala/repetição → squad. O squad gera a *matéria-prima*; o acabamento de marca é humano.

## 4. Checklist ao criar um squad novo

1. **Interno ou de entrega?** (a autonomia é gate pelo raio de impacto — princípio #3.)
2. **Um resultado** (workflow) — um squad, um resultado.
3. **Papéis** dentro dele (nunca sub-squad por plataforma/formato).
4. **Tools:** reusar MCP/skill existente; criar nova só se não existir.
5. **Config de cliente** (voz, regras, chaves) isolada por `client_id`.
6. **Guardrails:** `max_iterations`, orçamento por API, ponto de HITL.
7. **Nome-padrão:** prefixo `eg_` (marca squad autoral da EG) e nome pela **função**, nunca pela plataforma (`eg_criativos`, não `ads_meta`). Party.csv canônico: `agent_name,role,displayName,icon,file_path` com paths `./agents/`.
8. **Prompts versionados** (nunca soltos no código).
9. **Zero vazamento:** o mesmo squad serve dois "clientes" via config, sem misturar contexto.
10. **Registrar** a ideia/decisão no Banco de Ideias (Curador) e o porquê no Banco de Arquitetura (Arquiteto). Não documente inventário aqui — lê-se do repo vivo.

## 5. Integrações e config de cliente (ponteiros)

- **Integrações/MCPs ativos** → `.mcp.json`. Regra: **API direta antes de MCP** — embrulha uma tool em MCP só quando um 2º squad precisa reusá-la (barato de fazer depois, caro de manter cedo demais).
- **Config de cliente** isolada em `clients/<id>/` por `client_id`. Quando o cliente opera Kommo via EG, ganha dois arquivos além do config padrão: `kommo_config.json` (estruturado: `pipeline_stages`, `fields`, `routing_rules`, `templates`, `automations`, `plan`, `waba`, `pending`) e `kommo_context.md` (o porquê das decisões). Template em `clients/_template/`.
- **Roadmap de integrações** (templates de tarefa ClickUp, GitHub↔ClickUp, BI embutido, tráfego pago via MCP) → vive no Banco de Ideias, não aqui.
