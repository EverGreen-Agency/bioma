# 🌱 Manual Operacional Bioma v2 — Projetos e Tarefas

> **Substitui** a parte de estrutura/listas dos manuais v1 (Growth, Social, Tech).
> Os v1 seguem válidos como referência de **método** (o que cada status significa,
> quais campos preencher). Este v2 rege a **estrutura** no Bioma.
>
> Decidido em 29/07/2026 com o Eduardo. Data de vigência: a partir da
> repopulação da base (a base local foi zerada; produção começa vazia).

---

## 1. Por que existe um v2

Os manuais v1 foram escritos para o ClickUp e carregam decisões que eram
**limitação de ferramenta, não método**. A mais importante está declarada no
próprio Manual Social:

> *"E também por um limitação que a plataforma tinha de que uma lista mantém seu
> status independente da view, o que não permitiu nós segmentarmos status
> diferentes para essas duas demandas (Growth e Social Media)"*

No Bioma o status é por tarefa (`eg_tasks.status`) e o agrupamento é separado
(`group_status`). **Status diferentes convivem na mesma estrutura.** A razão de
existirem listas separadas deixou de existir — o que abriu espaço para
reorganizar por significado em vez de por contorno técnico.

---

## 2. Os três níveis (e o que cada um resolve)

| Nível | O que define | Onde vive |
|---|---|---|
| **Frente** | O **vocabulário**: status, campos obrigatórios, definição de pronto | `eg_task_lists.type` |
| **Projeto** | O **escopo e o prazo**: contrato, fases, datas, roadmap | `projects` + `eg_tasks.project_id` |
| **Tarefa** | A **unidade de trabalho** | `eg_tasks` |

### Por que Frente e Projeto são coisas diferentes

Foi a decisão central. Colapsar os dois quebra num dos lados:

- **Só frente** → não separa os 3 contratos da Univet (site, app V1, app V2).
- **Só projeto** → obriga a redefinir os status de Tech a cada projeto novo,
  mesmo quando *"passou pelas mesmas fases"* (palavras do Eduardo sobre a Univet).

Frente é gramática. Projeto é escopo. Uma frente Tech, três projetos dentro.

```
Univet Safety
└── Frente: Tech & Software          ← status BRAIN…DEPLOYED (uma vez)
    ├── Projeto: Site                ← contrato 1 · fases · datas → Gantt
    ├── Projeto: App V1               ← contrato 2 · entregue
    └── Projeto: App V2               ← contrato 3 · datas próprias → Gantt
```

### Projeto é campo da tarefa — mas referência, não texto

A proposta original do Eduardo foi *"projeto se tornar um campo da lista de
tarefas"*. Está correta na intenção (campo, não lista) e foi adotada — com uma
correção técnica: é **chave estrangeira** para `projects`, não texto livre.

Motivo: campo de texto criaria um **terceiro** conceito de projeto, solto dos
outros dois, com três consequências práticas:

1. **Deriva de nome** — "App V1", "app v1", "V1" viram coisas diferentes no filtro.
2. **Mata o Gantt** — roadmap precisa de data de início/fim, que vivem em
   `project_phases`. Texto não alcança.
3. **Perde o contrato** — os 3 contratos da Univet são 3 `project_contracts`.
   Sem referência, a tarefa nunca sabe se o escopo está dentro do que foi vendido.

Na tela funciona como o Eduardo imaginou: dropdown, filtro, agrupamento.

---

## 3. As frentes

### 3.1 Growth & Projetos (`type = 'growth'`)

Tráfego, CRM, sites, automação, demandas pontuais. Tarefa = entregável,
campanha ou rotina.

| Grupo | Status |
|---|---|
| NOT_STARTED | 🧠 BRAIN |
| ACTIVE | 📋 BACKLOG · 🏃 IN PROGRESS · 🔎 IN REVIEW · ❌ REJECTED · 🛑 BLOCKED |
| DONE | 🟩 DONE |
| CLOSED | ✅ CLOSED |

Campos: Área do Projeto, Prioridade, Esforço, Gestor da Conta, Verba,
Link do Doc, Responsável, Dono.

### 3.2 Tech & Software (`type = 'tech'`)

Feature, Bug/Fix, Chore. Toda tarefa acionável e testável.

| Grupo | Status |
|---|---|
| NOT_STARTED | 🧠 BRAIN · 🧊 BACKLOG · 📋 TO DO (SPRINT) |
| ACTIVE | 👨‍💻 IN PROGRESS · 🔎 CODE REVIEW · 🧪 QA / TESTING · 🛑 BLOCKED |
| DONE | 🚀 READY FOR RELEASE · 🚫 CANCELLED / WON'T FIX |
| CLOSED | ✅ DEPLOYED |

Campos: Tipo, Esforço (Fibonacci), Prioridade, Ambiente, GitHub PR, Módulo/Épico.

**Nota:** o v1 amarrava a nomenclatura de branch/commit ao ID do ClickUp
(`#EG-102`). No Bioma o equivalente é o ID da tarefa do Bioma — a integração
GitHub já existe (`project_github_connections`).

### 3.3 Social Media (`type = 'social'`) — **muda de casa**

**Decisão:** Social vira **aba dentro do Estúdio IA**, mantendo a esteira de
status. Não compete mais com Growth/Tech na aba Tarefas.

Razão: ideação, roteirização e produção já vivem no Estúdio IA (retrospectiva
de conteúdo, banco de ganchos, geração de roteiros). Manter uma lista de
tarefas paralela duplicaria o mesmo trabalho em dois lugares.

| Grupo | Status |
|---|---|
| NOT_STARTED | ⚪ IDEAÇÃO |
| ACTIVE | 🟡 ROTEIRIZAÇÃO · 🟠 EM PRODUÇÃO · 🔵 REVISÃO INTERNA · 🟣 APROVAÇÃO CLIENTE · 🔴 EM AJUSTE |
| DONE | 🥬 AGENDADO · 🌲 PUBLICADO · 🗽 ANALISAR (D+7) · 🚫 DESCARTADO |
| CLOSED | ✅ FINALIZADO |

Campos: Missão, Plataforma, Formato, Data Publicação, KPI Primário,
Link da Pasta, Arquivo Final, Legenda/Copy, Gancho.

> ⚠️ **Bug corrigido nesta decisão:** a migração do ClickUp mapeou `AGENDADO`
> para o grupo `NOT_STARTED` em 27 tarefas. Pelo manual, `AGENDADO` é **DONE**.
> A base foi zerada (backup em `scratch/backups/`), então o mapeamento correto
> vale desde a repopulação.

---

## 3.4 A própria EverGreen (dogfooding)

A EG é um workspace como qualquer outro — `kind = 'agency_internal'`, chamado
**Operação EG**. Ele sempre existiu, mas não tinha aba de Tarefas: era
impossível usar o próprio produto para gerenciar a casa. Corrigido.

O modelo é o mesmo dos clientes, sem estrutura paralela:

| Demanda interna | Onde vive |
|---|---|
| Tech da EG (o próprio Bioma, automações) | Frente **Tech** na Operação EG, projeto por iniciativa |
| Growth da EG (nosso tráfego, nosso site) | Frente **Growth** na Operação EG |
| Social da EG | Estúdio IA da Operação EG (mesma regra dos clientes) |
| Treinamento de time, processo, RH | Frente **Growth** ou **Geral**, projeto "Operação" |
| Hackathon | **Projeto** dentro da frente Tech, com datas → aparece no roadmap |
| Tarefa pessoal do CEO | Tarefa na Operação EG com você como responsável |

**Por que projeto e não lista para hackathon:** hackathon tem começo, fim e
escopo — é exatamente a definição de projeto. Como projeto tem datas, ele entra
no Gantt junto com o resto; se fosse uma lista, ficaria fora do roadmap.

### O Cockpit precisa ver as duas coisas

O painel "Minhas tarefas" lia apenas a tabela `deliverables` (do client-hub,
responsável por e-mail). O sistema que substituiu o ClickUp é `eg_tasks`
(responsável por FK). **As duas nunca se falavam**, então nada criado em
Tarefas aparecia no Cockpit.

Hoje `GET /tasks/me` atravessa a carteira inteira **mais** o workspace interno,
e o painel mostra as duas origens rotuladas. É isso que faz "entrar no cockpit e
ver todas as tarefas, de cliente e operacionais" funcionar de fato.

> As duas tabelas continuam existindo de propósito: `deliverables` é o que move
> o fluxo de aprovação do cliente; `eg_tasks` é a operação. Unificá-las é uma
> decisão em aberto, não uma pendência óbvia.

---

## 4. Checklist vs Subtarefa

Distinção que existia na prática mas **nunca foi documentada**. Registrada aqui
com as palavras do Eduardo:

> *"checklist eram etapas da mesma tarefa. Já as subtarefas era quando tinha
> alguma mudança de prazo, de responsabilidade, principalmente. Então, quando
> não dependia mais de mim, era de outra área, era de outra equipe."*

**As duas funcionalidades se mantêm**, porque resolvem problemas diferentes:

| | Checklist | Subtarefa |
|---|---|---|
| **O que é** | Etapas da **mesma** tarefa | Trabalho que **trocou de mão** |
| **Critério** | Mesmo responsável, mesmo prazo | Muda responsável **ou** muda prazo |
| **Gatilho típico** | "fazer capa", "inserir legendas" | passou para outra área/equipe |
| **Tem responsável próprio?** | Não | **Sim** |
| **Tem prazo próprio?** | Não | **Sim** |
| **Tem status próprio?** | Não (só feito/não feito) | **Sim** (mesma esteira da frente) |
| **Entra no Kanban?** | Não | **Sim** |
| **Tabela** | `eg_task_subtasks` | `eg_tasks` com `parent_task_id` |

### Consequência técnica

A tabela `eg_task_subtasks` de hoje tem só `title` + `is_completed` — ou seja,
**é um checklist**, apesar do nome. Está correta para o papel de checklist.

Subtarefa de verdade precisa de responsável, prazo e status próprios — portanto
é uma **tarefa com pai** (`eg_tasks.parent_task_id`), não uma linha em
`eg_task_subtasks`. É isso que permite o caso que o Eduardo descreveu: quando o
trabalho deixa de depender dele e vira de outra equipe, a subtarefa aparece no
Kanban **daquela** equipe, com o prazo **dela**.

Regra prática para o time:

> Se muda quem faz **ou** quando entrega → **subtarefa**.
> Se é só uma etapa sua dentro da mesma entrega → **checklist**.

---

## 5. Visualizações

Consolidadas dos três manuais v1 (eles pediam as mesmas três, com nomes
diferentes):

| Visão | Para quem | Conteúdo |
|---|---|---|
| **Quadro (Kanban)** | Time, dia a dia | Agrupado por status. Esconde BRAIN/BACKLOG e cancelados. |
| **Lista** | Gestor, planejamento | Agrupado por status. Mostra backlog para estimar esforço e priorizar. |
| **Roadmap (Gantt/Timeline)** | Cliente | Baseado em datas de início/fim. Agrupado por **projeto**. |

Filtros que os v1 pediam e devem existir como filtro, não como visão separada:
**Bug Tracker** (Tipo = Bug), **Banco de Ideias** (status = IDEAÇÃO),
**Aprovação** (status = APROVAÇÃO CLIENTE).

**Nas três visões deve ser possível criar tarefa.** Hoje só o Kanban permite —
lacuna registrada.

---

## 6. Detalhe da tarefa

O v1 tratava a descrição como **Definição de Pronto** ("Definition of Done") e
isso deve continuar explícito no Bioma — não como campo de texto solto, mas
rotulado, porque é o critério que autoriza mover para DONE.

Elementos do detalhe:

- **Definição de Pronto** (descrição) — o que precisa ser verdade para fechar
- Campos da frente (ver seção 3)
- **Checklist** — etapas próprias
- **Subtarefas** — trabalho delegado a outra mão/prazo
- **Dependências** — `eg_task_dependencies` (o "Waiting On" do v1, que ligava
  Growth aguardando Social)
- **Comentários** — histórico da conversa sobre aquela tarefa

O v1 de Growth já previa a dependência entre frentes; a tabela existe e deve
ser usada em vez de recriar.

---

## 7. Portal do cliente

Os três manuais v1 convergem numa regra que **se mantém integralmente**:

> **A Regra do Link Único.** O cliente recebe um link só. Tudo que ele precisa
> acompanhar ou aprovar está atualizado ali.

No Bioma isso é o Hub do Cliente, com os módulos ligados/desligados por
contrato (`enabled_modules`) — o que já resolve nativamente o
"se não contratou Social, este bloco é excluído" que o v1 fazia à mão.

---

## 8. O que ficou pendente de decisão

- **Recorrência.** O v1 de Growth usava a recorrência nativa do ClickUp para
  rotinas ("Otimização Semanal de Campanhas"). `eg_tasks.recurrence` e
  `recurrence_source_task_id` existem; a regra de negócio (quando recriar,
  o que copiar) não foi definida.
- **Campos personalizados criados pelo usuário.** Decidido **não** implementar
  agora: só os campos já existentes nos manuais v1. Reavaliar se aparecer
  demanda real de cliente.
- **Time tracking.** O v1 fala de "cronômetro rodando" por grupo de status.
  Não existe no Bioma e não foi priorizado.
