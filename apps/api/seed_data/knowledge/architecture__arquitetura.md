<!-- Banco de Arquitetura EG — o PORQUÊ da estrutura, não o inventário do filesystem. -->
<!-- Quem audita aqui é o Arquiteto (squad eg_arquiteto), lendo o repo AO VIVO. -->
<!-- Não liste squads/arquivos aqui: isso se lê do código. Registre só decisões e princípios. -->
# Banco de Arquitetura EG

> Este documento guarda o que **não dá pra ler no código**: a **identidade** da EverGreen, os **princípios de engenharia** da casa e as **decisões arquiteturais** (o *porquê* de cada escolha estrutural).
>
> O **inventário vivo** — quais squads existem, qual stack, quais integrações — **não mora aqui**. Ele é lido direto do repo pelo Arquiteto (`squads/*/squad.yaml`, `stack.json`, `.mcp.json`, o código) e exibido ao vivo na aba **Arquitetura** do dashboard (Mapa de Squads). Espelhar o filesystem num doc só cria divergência.
>
> Atualizado: 2026-06-25.

---

## 0. Identidade

- **Empresa:** EverGreen MKT — boutique de crescimento e consultoria comercial executiva (AI-First, orientada a dados). Não é agência 360.
- **ICP:** B2B, foco em integradoras de energia solar (faturamento > R$ 150 mil/mês), operação madura, dono presente.
- **Repo:** `evergreen-ai-os` — o "AI OS" da agência. Monorepo: framework de orquestração + squads + dashboard.

---

## 1. Princípios de Engenharia da Casa

Estes são os critérios contra os quais o **Gate de Princípios** do Arquiteto mede qualquer ideia ou projeto interno. São lei até serem revisados aqui.

- **Motor antes da interface.** Primeiro a lógica que funciona (squad, dado, regra); a tela vem depois e reflete o motor. Nunca uma UI bonita sobre um motor que não existe.
- **HITL (Human-in-the-loop).** Tudo que sai da máquina pro mundo (ClickUp, Kommo, ads, e-mail) passa por aprovação humana antes de escrever. A IA propõe; o humano libera.
- **Write/Read barrier.** A IA **lê** livremente (repo, bancos, plataformas), mas só **escreve** com aprovação explícita. Vale também pra auto-modificação: nenhum agente reescreve prompt/estrutura sozinho.
- **Isolamento por `client_id`.** Credenciais e dados de cliente nunca se misturam. Tokens de cliente jamais no `.env` global — ficam por cliente, isolados.
- **Dogfooding.** A EG roda nos próprios squads antes de vender o método. Se não serve pra gente, não vende.

---

## 2. Decisões Arquiteturais (o porquê)

> Onde registramos *por que* a estrutura é como é. Cada decisão é um ADR enxuto: contexto → escolha → porquê. O Arquiteto propõe novas entradas aqui (com aprovação) quando uma escolha estrutural se firma.

### D1 — Framework em Markdown/YAML interpretado, não em código

**Contexto:** precisávamos orquestrar múltiplos agentes. **Escolha:** squads são `squad.yaml` + `.agent.md` lidos pelo Claude Code, não um runtime em código. **Porquê:** versionável em git, editável por humano sem build, e o próprio LLM interpreta — zero camada de execução pra manter. O custo é não ter garantia de tipos; mitigado por convenções (formato do party.csv, schema dos bancos).

### D2 — Bancos em JSON/MD versionados, não em banco de dados

**Contexto:** Banco de Ideias, Stack e Arquitetura precisam persistir. **Escolha:** arquivos JSON/MD no repo, não um BD. **Porquê:** portabilidade (não somos reféns de infra), histórico no git de graça, e o dashboard lê/escreve via endpoints simples. Trade-off: não escala pra milhares de registros nem concorrência pesada — aceitável na escala de uma boutique. Migrar pra BD é uma decisão futura registrada no Banco de Ideias (`banks-portability`), não um default.

### D3 — Dashboard lê o filesystem ao vivo, não um estado duplicado

**Contexto:** o cockpit precisa mostrar squads e estados. **Escolha:** o `squadWatcher` (plugin Vite) escaneia `squads/`, lê `state.json` e os bancos, e serve via REST + WebSocket; o front não guarda verdade própria. **Porquê:** uma fonte só (o repo). O dashboard é janela, não cópia. Mesma filosofia do Arquiteto: ler a realidade, não um espelho.

### D4 — Arquiteto lê o repo ao vivo; este doc guarda só o porquê

**Contexto:** a primeira versão tinha um catálogo de squads escrito à mão aqui — e um squad "Cartógrafo" só pra sincronizá-lo. **Escolha:** eliminamos o Cartógrafo; o Arquiteto lê `squads/`, `stack.json` etc. direto, como um engenheiro faria. **Porquê:** um inventário escrito à mão **sempre** diverge do código. O agente já sabe ler arquivos — duplicar isso num doc e criar um squad pra ressincronizar era fragmentação pura. Este doc fica só com o que o código não diz: princípios e decisões.

### D5 — Curador, Arquiteto e Engenharia são papéis distintos

**Contexto:** risco de um agente "faz-tudo" que decide ideia, estrutura e código. **Escolha:** três perguntas, três donos. **Curador** (eg_banco_ideias): "essa ideia é nova no banco?". **Arquiteto** (eg_arquiteto): "isso cabe na arquitetura ou pede squad/stack nova?". **Engenharia** (eg_engenharia): "como construir um projeto — de cliente ou interno — via spec→ADR→scaffold?" (ver D6). **Porquê:** separar a curadoria de ideia, a vigilância de estrutura e a execução de projeto evita conflito de interesse e mantém cada parecer focado. O Arquiteto roda muitas vezes *depois* do Curador.

### D6 — A Engenharia serve projeto interno também (alvo é config, não squad novo)

**Contexto:** a Engenharia (SDD+ADR) nasceu para projeto de cliente, e por um momento o Especificador chegou a *rejeitar* trabalho interno, mandando pra um `eg_guardiao`. Mas a EG vai construir os próprios sistemas (ex: a "mega plataforma" — o EG AI OS produtizado), e isso é *build*, não auditoria. **Escolha:** o mesmo `eg_engenharia` atende cliente e interno; o alvo (`target`: `client`/`internal`) é configuração que muda só de onde vem o brief e onde moram os artefatos (cliente: `clients/<id>/engenharia/`; interno: `_opensquad/_memory/engenharia/<id>/`). **Porquê:** (1) o princípio "squad por função, não por cliente" — um squad de build separado por origem é a mesma duplicação que o princípio proíbe, só fatiada por interno/externo. (2) A "separação dura interno×entrega" é sobre *autonomia/raio de impacto*, não sobre repositórios separados; e a Engenharia tem raio baixo por construção — seu output são specs/ADRs/scaffold, todos com gate HITL, nada age em sistema vivo de cliente. Logo o alvo não altera a autonomia: os gates HITL valem igual. (3) Dogfooding é princípio da casa. **Fronteira:** *auditar* estrutura interna ("isso cabe?") continua sendo parecer do Arquiteto, não build; *construir* algo interno é da Engenharia. **Mitigações:** contexto injetado por id a cada run (sem context bleeding); HITL é propriedade do squad, não do alvo (sem autonomy creep).

### D7 — Mega-plataforma: multitenant primeiro, cada módulo em 3 fases, moat ≠ aprisionamento

**Contexto:** a EG vai construir seu próprio sistema operacional (o EG AI OS produtizado — `mega-plataforma` no Banco de Ideias), englobando backoffice interno + área do cliente e, no futuro, produto white-label. Risco: desenhar módulos acoplados a uma fase só (só interno, ou só cliente) e ter que reescrever a cada fase. **Escolha:** (1) **Multitenant/SSO/isolamento de dados é a fundação** — construído ANTES de client-hub, billing e do modelo de agências-parceiras (todos dependem dele). (2) **Cada módulo é um bloco reutilizável que atravessa 3 fases sem reescrever:** interno/operacional EG (dogfooding) → com/para o cliente → produto/white-label. (3) **Retenção pelo moat, não por trava:** o cliente fica porque sair dói operacionalmente (perde BI/score/histórico), **nunca** por backdoor de travamento — vetado (risco jurídico/LGPD); retenção legítima = suspensão de acesso em `mod-saas-billing`. **Porquê:** o custo de multi-tenant + modularidade upfront é menor que reescrever cada módulo a cada fase; e o moat operacional é defensável e ético, o backdoor não. O isolamento por `client_id` (princípio §1) generaliza aqui para `tenant_id` + RLS no Postgres. **Nota de posicionamento:** a plataforma é diferencial (moat), não transforma a EG em "agência 360" — a boutique é premium/seletiva/método e **não nichada por mercado** (solar é ICP momentâneo, não estrutural). Blueprint de referência reaproveitável: a proposta HM Conexões (`Proposta_..._v3.pdf`) é um protótipo single-tenant a generalizar. Detalhe da visão em `banco_ideias/docs/mega-plataforma.md`.

---

## 3. Glossário rápido

- **Squad** — time de agentes com pipeline próprio (`squads/<nome>/`).
- **Banco** — arquivo de verdade versionado (Ideias = `ideas.json`, Stack = `stack.json`, Arquitetura = este `.md`).
- **Gate** — verificação que o Arquiteto roda (Squad / Integração / Stack / Princípios).
- **Anel (ring)** — estágio de adoção de uma tech no Banco de Stack: assess → trial → adopt; ou hold (evitar).
- **HITL** — Human-in-the-loop. **ADR** — Architecture Decision Record (decisão registrada com o porquê).
