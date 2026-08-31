# Backlog de ideias do Bioma — o que foi decidido e ainda não foi construído

Documento vivo. Existe porque muita coisa boa foi conversada e decidida sem
virar código no mesmo dia — e ideia não registrada vira retrabalho ou some.

**Regra deste arquivo:** cada item diz *o que é*, *por que foi adiado* e *o que
destrava*. Item sem "o que destrava" é desejo, não backlog.

Última atualização: 2026-07-31.

---

## 0. A decisão de flexibilidade (releitura frequente)

Eduardo perguntou mais de uma vez se não vale abrir tudo para configuração —
dashboard e tarefas. A resposta que ficou, e o porquê:

**Existem três níveis de flexibilidade, com custos muito diferentes.**

| Nível | O que é | Custo | Decisão |
|---|---|---|---|
| **1. Configuração** | features fixas, ligadas/desligadas por cliente | baixo | **SIM** — já existe (`enabled_modules`, status por frente) |
| **2. Composição** | biblioteca de blocos montáveis por cliente | médio | **SIM, é o caminho** — widget construído para um cliente vai para a biblioteca e é ativado no próximo |
| **3. Definição** | usuário cria entidades, campos e lógica novos | altíssimo | **NÃO** — é reconstruir Airtable/Looker/Kommo |

**Por que o nível 3 fica fora:**
- é uma categoria de produto inteira (Metabase, Superset, Airtable levaram anos);
- não diferencia a EG — ninguém contrata agência pelo construtor de dashboard;
- todo relatório vira "depende de como o cliente configurou", o que mata a
  possibilidade de comparar clientes (o rollup da carteira, por exemplo, só
  existe porque o modelo é compartilhado);
- quando a necessidade de query arbitrária aparecer de verdade, a saída é
  **embutir** um Metabase ou expor camada SQL somente-leitura — não construir.

**Condição que faz o nível 2 funcionar:** o modelo de dados por baixo precisa ser
compartilhado. Se o pipeline da Univet virar tabela sob medida, nenhum widget é
reaproveitável e a "biblioteca" vira pasta de coisas incompatíveis. Por isso a
ordem é: **normalizar o modelo primeiro, widgets compõem por cima.**

Mesma régua vale para tarefas: configuração sim (status por frente), composição
talvez (campos personalizados escolhidos de um catálogo fechado de tipos),
definição não.

---

## 1. Copiloto — a visão completa

**O que o Eduardo quer, na palavra dele:** o Bioma não é só backoffice, é quase
um provedor de LLM — um Claude/ChatGPT/Gemini, só que específico da EG, com
acesso aos documentos da casa, já configurado para agir como a EG quer, com
fluxo programado, e sem prender a operação a uma ferramenta de terceiros.

### 1.1 O que JÁ existe (2026-07-31)

- Motor com **catálogo fechado de ações** (`bioma_worker/copilot.py`)
- **Execução real** do que é reversível, com `undo_hint`; ação visível ao
  cliente volta como `pending_confirmation`
- **Fonte obrigatória** em toda resposta (dado do Bioma cita tabela/tela; web só
  aceita URL realmente visitada)
- **Memória persistente** global (EG) e por workspace, versionada em
  `agent_memory_revisions`, com proveniência humano/agente
- **Skills** propostas pelo copiloto, com aprovação humana antes de valer
- Superfície: `/` no chat da tarefa

### 1.2 A peça que falta e muda tudo: ponte com `ai_workflow_runs`

Existem **dois sistemas que não se falam**:

- **Copiloto**: executa ações reais, mas **um passo por vez**
- **`ai_workflow_runs`**: multi-etapa, com checkpoint HITL, versionado e
  auditado — e já tem um template `client-onboarding` cujas etapas são
  exatamente escopo → arquitetura operacional → CRM/integrações → acessos →
  handoff. **Só que ele gera TEXTO**: descreve o que fazer, não executa.

**O que construir:** o copiloto propõe um *workflow* cujas etapas executam ações
reais do catálogo, com o humano aprovando o plano antes de rodar.

Ação nova necessária: `propose_workflow` — irreversível por natureza, então cai
na regra de confirmação humana já aprovada.

**O que isso destrava** (os três casos que o Eduardo descreveu):

1. *"Quero roteiro novo para os próximos anúncios"* → detecta o cliente pelo
   contexto da tela → roda a retrospectiva sozinho → gera roteiros → devolve as
   perguntas que faltam, em vez de exigir formulário preenchido
2. *"Quero cadastrar cliente/projeto novo"* → identifica se é projeto interno da
   EG ou hub de cliente → plano de N passos (criar org, workspace, liberar
   módulos, criar projeto, configurar financeiro/quadro societário, gerar posts
   iniciais, pesquisar o que já existe) → aprova → executa com checkpoint
3. *"Quero participar do hackathon X"* → ativa skill de hackathon → pesquisa o
   evento → cruza com o banco de ideias e o que a EG já fez → monta material

### 1.3 O que precisa MUDAR no que já existe

- **Skills viram executáveis.** Hoje são texto no dossiê (o modelo lê e segue).
  Na visão do Eduardo, uma skill é uma sequência de ações do catálogo — um
  procedimento que roda, não um parágrafo que orienta.
- **Inferência de contexto.** Hoje `workspace_id` é passado explicitamente; o
  copiloto precisa deduzir da tela e do histórico da conversa.
- **Aba de personalização** (inspirada no Claude: Habilidades, Conectores,
  Preferências). Hoje memória e skills estão espalhadas em duas telas — vira uma
  seção só, com cara de produto.
- **Biblioteca de skills** compartilhável entre workspaces, com origem e uso
  visíveis (`use_count` já existe no schema).

### 1.4 Superfícies pendentes

- `/` no Estúdio IA
- Chat de escopo global ("o que priorizar hoje?") — motor e dossiê já suportam,
  falta só a UI

---

## 2. Relação com Opensquad, squads, agentes e harness

Pergunta do Eduardo: como lidar com isso daqui para frente — implementar, manter
e estruturar dentro do código.

**O diagnóstico honesto:** hoje existem **três máquinas de IA** no repositório,
com sobreposição real:

| Máquina | Onde | O que faz | Estado |
|---|---|---|---|
| **Opensquad** | `_opensquad/`, `squads/` | orquestração multi-agente em arquivos, roda fora do produto (via Claude Code) | usado para produzir trabalho, não é produto |
| **`squad_runner`** | `bioma_worker/squad_runner.py` | pilares (oferta/demanda/conversão/…) com schema fechado, uma chamada | dentro do produto |
| **`ai_workflow_runs`** | `services/ai_operations.py` | workflows versionados multi-etapa com HITL | dentro do produto, gera texto |
| **Copiloto** | `bioma_worker/copilot.py` + `services/copilot.py` | interpreta intenção e executa ações reais | dentro do produto, um passo |

**Direção proposta (não implementada):** convergir para **uma** máquina no
produto, com papéis separados:

- **Ações** (o catálogo do copiloto) = as ferramentas. Fonte única de verdade do
  que a IA pode fazer, com reversibilidade declarada.
- **Skills** = procedimentos reutilizáveis compostos de ações.
- **Workflows** = execução multi-etapa com checkpoint, orquestrando skills.
- **Squads/pilares** = *presets* de workflow com identidade e schema próprios —
  não uma máquina paralela.
- **Opensquad** continua fora do produto, como ferramenta de trabalho da EG
  (produzir specs, docs, análises). Não vira feature vendável.

**Por que isso importa:** hoje, adicionar uma capacidade nova exige decidir em
qual das três máquinas ela entra, e a resposta não é óbvia. Convergir reduz isso
a "é uma ação, uma skill ou um workflow?".

---

## 2-B. Absorção do Opensquad — análise medida (2026-07-31)

**Hipótese do Eduardo:** "o Bioma já sobressaiu o Opensquad; ele foi (ou falta
ser) absorvido, e os squads também. Daí só faltaria limpar o repo."

**Está certo em dois terços, e errado no terço que mais importa.** Medição:

| Parte | Tamanho | Situação real |
|---|---|---|
| `_opensquad/core/` (framework) | 69 arquivos | **superado** pelo copiloto + skills + planos + memória |
| `_opensquad/_memory/` (conhecimento) | 160 arquivos | **NÃO absorvido** — lido do disco em runtime |
| `squads/` (9 squads) | 4 MB | referenciado só como `source_ref` (string), não carregado |
| Total | 62 MB / 724 arquivos | |

### O achado que muda o plano

Quatro telas do produto leem `_opensquad/_memory/` **do disco, em runtime**:

- Banco de Ideias → `_memory/banco_ideias/ideas.json`
- Banco de Stack → `_memory/banco_stack/stack.json`
- Arquitetura → `_memory/banco_arquitetura/arquitetura.md`
- Engenharia → `_memory/engenharia/`
- (mais o Wiki, que importa manuais de `_memory/knowledge`)

E o próprio `routers/admin.py` documenta a consequência:

> "Fora do monorepo (produção Railway, onde `_opensquad/` não existe) as
> leituras respondem vazio e as escritas retornam 503 — é um recurso do
> ambiente de desenvolvimento EG."

Ou seja: **essas telas só funcionam na máquina do Eduardo.** Em produção elas
existem no menu e aparecem vazias. Isso é a mesma família de problema que a
auditoria de superfície morta vinha achando — feature que existe mas não
funciona onde importa —, só que aqui é por desenho, não por esquecimento.

### Consequência para a limpeza

Apagar `_opensquad/` hoje **quebra essas telas em dev** (em produção elas já não
funcionam). Então a ordem correta não é "limpar", é:

1. **Migrar o conteúdo para o Postgres** — ideias, stack, arquitetura e docs de
   engenharia viram tabelas. As telas passam a funcionar em produção pela
   primeira vez, e o dado deixa de depender de um clone do monorepo.
2. **Aposentar `_opensquad/core/`** — o framework de orquestração foi mesmo
   superado pelo que está no produto (catálogo de ações, skills aprovadas,
   planos multi-etapa, memória versionada).
3. **Decidir o destino de `squads/`**: os 9 squads viram *presets de workflow*
   no produto (a direção do §2), ou continuam como referência de trabalho fora
   dele. Hoje só existem como string em `source_ref` — nenhum código os carrega.
4. **Só então limpar o repo.**

**O que NÃO deve ser absorvido:** o Opensquad como ferramenta de trabalho da EG
(rodar squads via Claude Code para produzir specs, análises, documentos). Isso é
ferramenta interna de quem constrói, não feature vendável — e continua útil.

**Ganho colateral da migração:** com o conhecimento em banco, o copiloto pode ler
banco de ideias, stack e arquitetura como dossiê — hoje ele não consegue, porque
esses dados não existem para a API em produção.

---

## 3. Base44 — features mapeadas dos vídeos

Fonte: dois vídeos analisados pelo Eduardo em 2026-07-31. A tese central é que
IA/automação servem para **operar a agência de dentro para fora**, não só para
entregar marketing. Tratar serviço criativo/técnico como produto de software.

### 3.1 Feature A — Motor de Over-Delivery (expansão de escopo)

**O que é:** o cliente pede uma Landing Page; o sistema monta LP + CRM +
automação + agente de IA. Cada briefing vira oferta de algo que o cliente não
sabia que precisava.

**Como cai no Bioma:** ação/skill de "Expansão de Escopo" — ao analisar um
briefing ou um lead no CRM, o copiloto identifica lacunas no funil e sugere
composição (ex: pediu tráfego → sugere GTM + GA4 + CRO).

**Já existe base:** o pilar `opportunity_fit` e o gerador de propostas com
injeção de cases. Falta a lógica de *lacuna de funil* e a composição de pacote.

**Cuidado registrado:** não pode virar upsell automático sem revisão — cai na
regra de ação visível ao cliente (confirmação humana).

### 3.2 Feature B — Onboarding automatizado ponta a ponta

**O que é:** cliente dá o ok → onboarding dispara sozinho; sistema cobra acessos
e só libera a tarefa para a equipe quando todos os ativos estão no banco.

**Como cai no Bioma:** é o caso 2 do copiloto (§1.2) somado ao template
`client-onboarding` que já existe. O diferencial do Base44 é a **cobrança ativa
de acessos por WhatsApp** e o **gate**: a tarefa técnica só abre quando os
ativos chegaram.

**Já existe base:** providers de WhatsApp, cofre de acessos, tarefas com status.
Falta o gate automático e a cadência de cobrança.

### 3.3 Feature C — "Superagent" / Account Manager de IA

**O que é:** agente proativo que cobra feedback, manda atualização de status e
agenda a próxima reunião. Encerra o vai-e-vem infinito.

**Como cai no Bioma:** é a evolução mais ambiciosa e a que mais muda a operação.
Precisa de:
- **execução agendada** (cron) — o Bioma hoje só age quando alguém clica;
- disparo de WhatsApp com follow-up automático em 24h sem resposta;
- **transcrição de áudio do cliente** virando comentário na tarefa (o cliente
  responde por áudio — isso é real no Brasil);
- regra clara de quando o agente fala com o cliente sem humano no meio.

**Cuidado registrado:** isto é ação visível ao cliente por definição. A decisão
já tomada (confirmação humana antes de qualquer coisa que o cliente vê) precisa
ser revisitada explicitamente aqui — ou o Superagent não funciona, ou a regra
muda para "aprovação por cadência" (aprova o padrão uma vez, não mensagem a
mensagem). **Decisão pendente do Eduardo.**

### 3.4 Feature D — Repositório base / compressão de tempo ("Build Once")

**O que é:** projeto de 6 semanas vira 6 dias reaproveitando estrutura. O
copiloto atua como bibliotecário de código: cataloga lógica, clona repo base,
troca variáveis, faz deploy.

**Como cai no Bioma:** conecta com o Banco de Stack e o CodeGraph/graphify que
já existem. Falta o catálogo de *repositórios base* com deploy parametrizado.

**Cuidado registrado:** deploy automatizado é ação irreversível e cara de
errar — exige confirmação e ambiente de staging.

### 3.5 System prompt sugerido (registrado para referência)

O Eduardo trouxe um bloco de instruções para o "Base44 Copilot" com quatro
diretrizes: proatividade absoluta, expansão de escopo inteligente, mindset
"build once" e recusa a ferramentas engessadas (custom code, sem WordPress).

**Não aplicar como está.** O prompt do copiloto atual tem regras de honestidade
(fonte obrigatória, nunca afirmar sem evidência) que entram em conflito com
"proatividade absoluta" mal calibrada. A síntese é possível — proativo em
*sugerir*, conservador em *afirmar* — mas exige reescrita, não colagem.

---

## 4. Univet — CRM e dashboard flexível

**Contexto:** negociação em andamento (frente de lupas primeiro), múltiplas
frentes, venda por representantes internos e externos, pipelines diferentes.
Ainda não está decidido se ficam no Kommo.

**Modelo proposto (limitado mas real, nível 2 de flexibilidade):**
- `pipelines` por workspace (Univet teria "Direto" e "Representantes")
- `pipeline_stages` ordenados por pipeline (mesmo padrão de status por frente)
- `reps` (interno vs externo, comissão, contato)
- `deals` (evolução de `leads`: ganha `pipeline_id`, `stage_id`, `rep_id`)

**Dashboard desacoplado da escolha de CRM:** camada de relatório que lê de
tabela normalizada, alimentada por sync — mesmo padrão de Google Ads/Meta. Se
ficarem no Kommo, o Bioma sincroniza deals/reuniões de lá; se saírem, a fonte
muda e o dashboard não.

**Widgets parametrizados** (não tela fixa): catálogo pequeno —
calendário-de-reuniões, funil-por-estágio, ranking-de-representante,
tabela-de-negócios — aceitando `pipeline_id`, período e agrupamento.

**O que destrava:** a negociação fechar e a decisão de CRM sair. Construir antes
é apostar no formato errado.

---

## 5. Feature flags, testes e analytics

- **Feature flags por cliente → CONSTRUIR.** Pequeno (~200 linhas), e é core do
  modelo de negócio (liberação por cliente, "em breve", beta). Metade já existe:
  `CLIENT_MODULES` é lista fechada em código; falta estado por cliente/feature.
- **Analytics de produto (funil, retenção, replay) → INTEGRAR PostHog.**
  Construir é armadilha; é commodity.
- **A/B testing → NÃO FAZER agora.** Com ~4 clientes ativos não há significância
  estatística; qualquer resultado é ruído. A/B de verdade pertence às campanhas
  dos clientes (onde há volume), não ao produto. O substituto no tamanho atual é
  feature flag + conversa direta.

---

## 6. Itens menores já registrados em outros lugares

- **Recorrência de tarefas**: colunas existem (`recurrence`,
  `recurrence_source_task_id`), regra de negócio nunca definida — decisão do
  Eduardo
- **Campos personalizados por frente** vindos de `task-frentes.ts` (hoje é
  conjunto fixo em código)
- **Time tracking**: existe no manual v1, não existe no Bioma, não priorizado
- **`styles.css`**: quebrado em 8 arquivos por tamanho, não por domínio real —
  reorganização honesta por domínio fica como débito
- **Smokes não isolados por transação**: a ordem (`ORDER_FIRST`) resolve na
  prática; isolamento real é pendente
- **PAT sem escopo, sem rate limit próprio, sem rotação assistida** — ver
  `bioma/docs/api-externa.md`
- **Deliverables × eg_tasks**: dois sistemas coexistindo; unificar (ou não) é
  decisão de produto

---

## 7. Ruído de ferramentas (Gemini Spark e afins)

**Observação do Eduardo:** a briga entre ferramentas (Gemini Spark, Base44,
Claude, n8n…) causa ruído diário — qual usar, qual aplicar.

**Posição registrada:** isso é argumento *a favor* da tese do Bioma, não contra.
Ferramentas de terceiros mudam de preço, de API e de dono. O que não muda é o
**dado da operação da EG** e as **ações que o negócio precisa executar**. A
estratégia consistente é:

- manter no Bioma o que é **específico da EG** (modelo de dados, ações,
  memória, procedimentos) — é isso que não dá para comprar pronto;
- tratar provedor de LLM como **peça trocável** — o control plane de roteamento
  já existe justamente para isso;
- integrar (não reconstruir) o que é **commodity**: analytics de produto,
  transcrição, busca web.

Gemini Spark é agentic assistant com MCP e execução em VM — relevante como
*possível provedor/executor*, não como concorrente do Bioma. Se um dia fizer
sentido, entra como mais uma conta no control plane.

---

## Ordem sugerida de ataque

1. ~~**Documentação da API + Fóton**~~ — feito em `bioma/docs/api-externa.md`
2. ~~**Feature flags por cliente**~~ — feito (`0071`, catálogo em
   `bioma_api/feature_flags.py`, smoke próprio)
3. ~~**Copiloto executável multi-etapa** (§1.2)~~ — feito (`0072`,
   `copilot_plans`, 7 regras de segurança validadas em smoke)
4. **Migrar `_opensquad/_memory` para o Postgres** (§2-B) — destrava 4 telas que
   hoje só funcionam em dev, e só depois disso a limpeza do repo é segura
5. **Aba de personalização unificada** (§1.3) — hoje memória, skills e planos
   estão em painéis separados; falta a cara de produto (estilo Claude)
6. **Superagent / cobrança ativa** (§3.3) — depende da decisão sobre cadência
7. **Modelo pipeline/rep da Univet** (§4) — depende da negociação
8. **Biblioteca de widgets** (§4) — depende do modelo normalizado
9. **PostHog** (§5) — quando houver volume de uso
