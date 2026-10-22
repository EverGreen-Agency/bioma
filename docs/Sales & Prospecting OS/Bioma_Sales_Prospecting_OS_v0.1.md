# Bioma Sales & Prospecting OS
## Documento de Visão, Escopo Funcional e Roadmap v0.1

**Produto:** Bioma  
**Contexto:** EverGreen Consultoria e Tecnologia  
**Versão:** 0.1  
**Status:** Documento de planejamento para decisão e implementação  
**Objetivo:** consolidar a visão discutida para transformar o Bioma em uma camada operacional e inteligente para onboarding, prospecção, vendas e gestão do trabalho de SDRs/Prospectadores.

---

# 1. Resumo executivo

O Bioma já possui uma proposta natural de centralização de contexto, inteligência e operação. A oportunidade discutida é ampliar essa proposta com um domínio de **Sales & Prospecting**, capaz de reduzir fragmentação entre ferramentas, dar contexto ao SDR e automatizar o trabalho administrativo que hoje ocorre entre listas de leads, CRM, telefone, WhatsApp, calendário, playbooks e acompanhamento gerencial.

A tese central é simples:

> O SDR não deveria gastar a maior parte do tempo operando ferramentas. O Bioma deve organizar o contexto, sugerir a próxima melhor ação, executar o administrativo e permitir que o SDR concentre energia em pesquisar, conversar, qualificar e agendar boas oportunidades.

Esse domínio combina quatro camadas:

1. **Prospecting Engine:** geração, importação, normalização, qualificação e priorização de leads;
2. **Commercial Core:** contas, pessoas, oportunidades, pipeline, tarefas, histórico e sessões de prospecção;
3. **Sales Knowledge & Enablement:** onboarding, motions, ICPs, playbooks, objeções, perguntas, cases e roleplays;
4. **Execution & Intelligence:** fila de trabalho, ligações, follow-ups, calendário, mensagens, automações, copiloto e análise de performance.

A recomendação desta v0.1 é **não tentar reconstruir de imediato um CRM, um discador, um Zapier, um LMS e uma plataforma de WhatsApp completos**. O Bioma deve possuir o **modelo de dados, a inteligência, o workflow e a experiência do usuário**, integrando fornecedores externos para scraping, telecomunicações, WhatsApp, calendário e outros canais quando fizer sentido.

---

# 2. Contexto e problema

A operação comercial da EverGreen está evoluindo de uma aquisição muito dependente de indicações e plataformas de freelancing para um modelo com prospecção ativa e maior previsibilidade.

A entrada de SDRs/Prospectadores cria uma necessidade adicional: o processo comercial precisa deixar de existir apenas na cabeça dos fundadores e passar a ser **ensinável, consultável, executável e mensurável**.

O problema não é apenas documentar o processo. Um PDF ou manual estático tende a perder utilidade rapidamente porque a rotina de prospecção exige respostas em segundos:

- Quem devo prospectar?
- Esse lead vale meu tempo?
- O que eu preciso descobrir antes de ligar?
- Como abordar?
- O que responder a essa objeção?
- Qual pergunta devo fazer agora?
- Quando agendar reunião?
- Quando desqualificar?
- O que registrar?
- Quando retornar?
- O que acontece automaticamente depois da ligação?

O Bioma pode responder essas perguntas usando contexto operacional + conhecimento comercial + automações.

---

# 3. Visão do produto

## 3.1. Definição

**Bioma Sales & Prospecting OS** é a camada do Bioma responsável por transformar dados e conhecimento comercial em ações de prospecção e venda.

Ele deve funcionar como o ambiente de trabalho do SDR, e não apenas como um CRM tradicional.

## 3.2. Princípio de design

Um CRM tradicional responde:

> “Qual é o estado atual deste lead?”

O Bioma Sales deve responder também:

> “O que eu deveria fazer com este lead agora?”

## 3.3. Resultado desejado

O SDR deve conseguir:

1. criar/encontrar uma lista de prospects;
2. revisar qualidade e prioridade;
3. iniciar uma sessão de prospecção;
4. abordar ou ligar sem montar contexto manualmente;
5. acessar perguntas, objeções e playbooks durante a conversa;
6. classificar o resultado em poucos segundos;
7. deixar o Bioma executar tarefas administrativas e automações;
8. seguir para o próximo lead;
9. aprender com feedback e resultados reais.

---

# 4. Princípios do domínio Sales

## 4.1. O vendedor trabalha; o sistema administra

A interface deve minimizar digitação, troca de abas e atualizações manuais de CRM.

## 4.2. Conhecimento no contexto da ação

Playbooks não devem existir apenas como páginas para leitura. Devem aparecer no momento em que são necessários.

## 4.3. AI-assisted, não AI-dependent

Regras críticas, guardrails e playbooks aprovados devem permanecer determinísticos. IA interpreta contexto, recupera conhecimento e sugere ações, mas não substitui regras comerciais essenciais.

## 4.4. Bioma como system of record comercial

No longo prazo, o Bioma deve possuir nativamente os objetos fundamentais da relação comercial. CRMs externos podem existir como conectores ou mecanismos de transição, não como dependência conceitual.

## 4.5. Integrações para infraestrutura commodity

O Bioma não deve construir do zero:

- rede telefônica;
- infraestrutura oficial de WhatsApp;
- scraping de cada fonte;
- provedor de calendário/videoconferência;
- envio de e-mail transacional.

Deve integrar esses serviços atrás de interfaces internas estáveis.

## 4.6. Aprender com a operação

Calls, respostas, objeções, pesquisas, conversões e perdas devem retroalimentar o conteúdo e a priorização.

---

# 5. Jornada operacional desejada do SDR

## Etapa 1 — Selecionar uma campanha/lista

Exemplo:

> Clínicas odontológicas — Florianópolis — Motion Growth

A lista pode ter sido criada por:

- Google Maps Scraper;
- importação CSV;
- pesquisa manual;
- fonte futura de dados;
- integração externa.

## Etapa 2 — Revisar prospects

O Bioma mostra:

- empresa;
- localização;
- telefone;
- site;
- reviews/nota quando disponíveis;
- origem;
- critérios de filtro;
- duplicidade;
- existência prévia no CRM;
- score/fit;
- possíveis sinais.

## Etapa 3 — Iniciar Prospecting Session

O SDR seleciona uma meta operacional, por exemplo:

- 50 ligações;
- 30 contas;
- 90 minutos;
- lista específica.

## Etapa 4 — Executar contato

O Bioma apresenta o lead atual com contexto e ações rápidas:

- ligar;
- abrir WhatsApp;
- abrir e-mail;
- registrar tentativa;
- abrir playbook;
- buscar card;
- perguntar ao Coach.

## Etapa 5 — Assistência durante conversa

O SDR pode acessar rapidamente:

- perguntas de discovery;
- objeções;
- battlecards;
- cases;
- guardrails;
- oferta/motion;
- histórico do prospect.

## Etapa 6 — Classificar resultado

Exemplos:

- não atendeu;
- número inválido;
- não interessado;
- pessoa errada;
- follow-up;
- qualificado;
- reunião agendada;
- nurture.

## Etapa 7 — Automação pós-contato

O Bioma executa, conforme regras:

- mover etapa;
- criar tarefa;
- reagendar tentativa;
- retirar da fila;
- registrar motivo;
- enviar mensagem permitida;
- agendar reunião;
- gerar briefing;
- notificar closer.

## Etapa 8 — Próximo lead

O sistema carrega automaticamente o próximo prospect elegível da fila.

---

# 6. Mapa funcional do módulo

```text
BIOMA SALES & PROSPECTING
│
├── Home / Today
├── Prospecting
│   ├── Find Leads
│   ├── Lists
│   ├── Imports
│   ├── Enrichment
│   ├── Scoring
│   └── Prospecting Sessions
│
├── CRM / Commercial Graph
│   ├── Accounts
│   ├── People
│   ├── Opportunities
│   ├── Pipeline
│   ├── Activities
│   └── Tasks
│
├── Sales Knowledge
│   ├── Motions
│   ├── ICPs
│   ├── Playbooks
│   ├── Questions
│   ├── Objections
│   ├── Battlecards
│   ├── Cases
│   ├── Offers
│   └── Guardrails
│
├── Call
│   ├── Queue
│   ├── Dialer
│   ├── Live Context
│   ├── Copilot
│   └── Disposition
│
├── Conversations
│   ├── WhatsApp
│   ├── E-mail
│   └── Call history
│
├── Calendar
│   ├── Availability
│   ├── Scheduling
│   └── Reminders
│
├── Learn
│   ├── Onboarding
│   ├── Tracks
│   ├── Roleplays
│   └── Progress
│
└── Insights
    ├── Funnel
    ├── Lists
    ├── Sessions
    ├── SDR performance
    ├── Content usage
    └── Knowledge gaps
```

---

# 7. Prospecting Engine

## 7.1. Find Leads

Objetivo: permitir que o SDR/gestor crie listas sem precisar operar diretamente cada fornecedor de dados.

### Entrada por formulário

Campos possíveis:

- categoria/segmento;
- cidade/região;
- quantidade desejada;
- rating mínimo;
- mínimo de avaliações;
- presença de website;
- tipo de telefone;
- palavras-chave;
- exclusões.

### Entrada por linguagem natural

Exemplo:

> “Encontre até 150 clínicas odontológicas em Florianópolis com pelo menos 30 avaliações, nota acima de 4,5 e telefone celular.”

A IA converte isso em uma especificação de busca estruturada.

## 7.2. Provider adapters

O domínio deve evitar acoplamento rígido a uma fonte específica.

Interface conceitual:

```text
LeadSourceAdapter
├── GoogleMaps/Apify
├── CSV
├── Manual
├── Provider futuro A
└── Provider futuro B
```

## 7.3. Normalização

Antes da importação definitiva:

- telefone em formato canônico;
- classificação celular/fixo quando possível;
- e-mail normalizado;
- domínio/site normalizado;
- cidade/UF normalizadas;
- nome empresarial limpo;
- origem preservada.

## 7.4. Deduplicação

Verificar:

- telefone;
- domínio;
- nome + cidade;
- endereço;
- identificador externo da fonte.

Classificar como:

- novo;
- provável duplicado;
- já existente;
- já prospectado;
- bloqueado/desqualificado.

## 7.5. Preview antes de importar

O usuário deve ver algo como:

```text
294 encontrados
121 atendem aos filtros
87 possuem telefone elegível
11 já existem no Bioma
76 novos prospects

[Revisar] [Importar 76]
```

## 7.6. Lead list / batch

Cada importação deve preservar a origem e os critérios usados. Isso permite mensurar futuramente quais listas e filtros realmente geram reuniões e receita.

---

# 8. Commercial Core / CRM nativo

## 8.1. Objetos fundamentais

### Account
Empresa ou organização.

### Person
Contato individual ligado a uma Account.

### Opportunity
Possibilidade comercial específica.

### Activity
Ligação, e-mail, mensagem, reunião ou evento relevante.

### Task
Ação futura com responsável e prazo.

### Conversation
Thread ou conjunto de interações por canal.

## 8.2. Objetos complementares

- Pipeline;
- PipelineStage;
- ProspectingList;
- ProspectingSession;
- CallAttempt;
- Meeting;
- LeadSource;
- Workflow;
- AutomationExecution.

## 8.3. Pipeline

O Kanban continua útil, mas não deve ser a home do vendedor.

A função principal é representar estado comercial.

Exemplo inicial de outbound:

1. Novo Prospect;
2. Tentativa de Contato;
3. Em Conversa;
4. Follow-up;
5. Qualificado;
6. Reunião Agendada;
7. Oportunidade;
8. Perdido / Nurture.

As etapas definitivas devem ser validadas com a operação real.

---

# 9. Prospecting Sessions

## 9.1. Conceito

Uma Prospecting Session representa um bloco real de trabalho comercial.

Em vez de medir apenas quantidade de atividades no CRM, o Bioma acompanha sessões com objetivo, lista, duração e resultado.

## 9.2. Exemplo

```text
Prospecting Session
SDR: Gustavo
Lista: Clínicas SP
Motion: Growth
Meta: 50 ligações

Ligações: 50
Conectadas: 19
Conversas: 13
Qualificadas: 5
Reuniões: 3
Follow-ups: 4
```

## 9.3. Benefícios

- foco operacional;
- comparação entre listas;
- análise por horário;
- coaching;
- produtividade;
- criação de cadência saudável;
- base para gamificação futura sem depender de métricas vazias.

---

# 10. Sales Knowledge & Playbooks

O conhecimento comercial não deve ser uma wiki tradicional. Ele deve ser modelado como objetos estruturados reutilizáveis.

## 10.1. Tipos de conteúdo

- principle;
- motion;
- ICP;
- signal;
- question;
- playbook;
- objection;
- battlecard;
- offer;
- case;
- guardrail;
- process;
- example.

## 10.2. Commercial Motions iniciais

### Motion Growth

Problema central: empresas que já vendem, mas têm aquisição/comercial sem previsibilidade.

### Motion AI & Automation

Problema central: processos manuais, repetitivos, caros ou fragmentados que consomem pessoas, tempo e capacidade operacional.

## 10.3. Playbooks iniciais

1. Pesquisa de prospect;
2. Primeira abordagem;
3. Lead respondeu;
4. Qualificação Growth;
5. Qualificação AI & Automation;
6. Objeção;
7. Follow-up;
8. Handoff SDR → Closer.

## 10.4. Card como unidade operacional

Uma card deve responder rapidamente:

- por que estou vendo isso?
- qual é meu objetivo?
- o que preciso descobrir?
- o que posso perguntar?
- o que devo evitar?
- qual é o próximo passo?

Exemplo:

```text
JÁ TEMOS UMA AGÊNCIA

Objetivo
Entender cobertura e possíveis lacunas.

Pergunte primeiro
“Hoje essa agência entra mais em mídia e comunicação
ou também participa da estrutura comercial e decisões
de crescimento?”

Evite
- atacar a agência;
- afirmar que a EverGreen fará melhor sem contexto;
- oferecer desconto.

Próximos caminhos
- cobre parcialmente → investigar gap;
- cobre tudo e está satisfeito → avaliar outra dor;
- está insatisfeito → aprofundar causa;
- sem gap → não insistir.
```

## 10.5. Modos de consumo

### Work
Consulta completa durante rotina.

### Call
Versão extremamente curta para uso ao vivo.

### Learn
Explicação, exemplos, exercícios e roleplay.

### Coach
Grounding para IA contextual.

### Insights
Uso, feedback e eficácia operacional.

A **Sales Content Spec v0.1** existente deve ser tratada como especificação editorial complementar deste documento.

---

# 11. Onboarding e Learn

## 11.1. Objetivo

Transformar onboarding em uma experiência progressiva e mensurável, não em entrega de PDFs.

## 11.2. Tracks sugeridos

### Track 1 — EverGreen e venda

- posicionamento;
- princípios;
- papel do SDR;
- guardrails;
- quando escalar.

### Track 2 — Growth

- ICP;
- sinais;
- perguntas;
- objeções;
- cases.

### Track 3 — AI & Automation

- ICP;
- processos;
- sinais;
- perguntas;
- objeções.

### Track 4 — Prospecção

- pesquisa;
- preparação;
- abordagem;
- follow-up.

### Track 5 — Qualificação

- problema;
- impacto;
- prioridade;
- decisão;
- fit.

### Track 6 — Operação Bioma

- listas;
- sessões;
- registros;
- tarefas;
- handoff.

### Track 7 — Roleplays

Simulações antes de atuação independente.

## 11.3. Regra de design

O Learn deve reutilizar o mesmo conteúdo do Work/Call. Não criar duas bases paralelas.

---

# 12. Call Queue e Power Dialer

## 12.1. Call Queue

A primeira evolução necessária não é necessariamente telefonia integrada. É uma fila estruturada de prospects elegíveis para contato.

A fila pode considerar:

- lista;
- prioridade;
- horário;
- número de tentativas;
- próxima atividade;
- owner;
- status;
- regras de exclusão.

## 12.2. Dialer V1

O SDR abre o lead e aciona uma ligação a partir da interface. Ao terminar, classifica o resultado e segue para o próximo.

## 12.3. Power Dialer

Após a classificação de uma ligação, o sistema carrega/disca sequencialmente o próximo prospect, reduzindo ações manuais.

## 12.4. Não priorizar inicialmente

Não há necessidade, no MVP, de:

- predictive dialer;
- múltiplas chamadas simultâneas;
- roteamento complexo de call center;
- URA completa;
- construção própria de infraestrutura PSTN.

## 12.5. Complexidade

**MVP:** alta-moderada.  
**Produção robusta:** alta.

A complexidade está menos na tela e mais em telecomunicações, estados de chamada, dispositivo/microfone, confiabilidade, callbacks, custos, gravação quando aplicável e requisitos operacionais.

---

# 13. Call Disposition

Ao finalizar uma ligação, o SDR deve conseguir classificar o resultado em poucos segundos.

## 13.1. Dispositions iniciais

- Não atendeu;
- Ocupado;
- Número inválido;
- Pessoa errada;
- Não interessado;
- Follow-up;
- Qualificado;
- Reunião agendada;
- Nurture;
- Outro.

## 13.2. Cada disposition pode disparar ações

Exemplo — Não atendeu:

```text
Incrementar attempt_count
↓
Se attempt_count < limite
    criar nova tentativa
    opcionalmente disparar mensagem permitida
Senão
    retirar da fila ativa
    mover para status definido
```

Exemplo — Follow-up:

```text
Solicitar data/hora
↓
Criar task
↓
Mover para Follow-up
↓
Reinserir na fila na data correta
```

Exemplo — Reunião agendada:

```text
Criar evento
↓
Mover etapa
↓
Registrar participante
↓
Gerar briefing
↓
Iniciar lembretes
↓
Notificar closer
```

---

# 14. Workflow Engine

## 14.1. Motivação

As automações pós-contato não devem ficar espalhadas como `if/else` hardcoded em vários serviços.

## 14.2. Modelo conceitual

```text
TRIGGER
↓
CONDITIONS
↓
ACTIONS
```

## 14.3. Triggers possíveis

- call.disposition_changed;
- opportunity.stage_changed;
- meeting.created;
- task.overdue;
- message.received;
- prospect.imported;
- retry_due;
- no_activity_for_period.

## 14.4. Conditions

- attempt_count;
- stage;
- owner;
- motion;
- source;
- tag;
- lead score;
- horário/dia;
- presença de telefone/e-mail;
- existência de reunião.

## 14.5. Actions

- move_stage;
- create_task;
- schedule_retry;
- enqueue/dequeue;
- mark_lost;
- send_message;
- create_meeting;
- notify_user;
- assign_owner;
- generate_briefing;
- call_webhook.

## 14.6. Fases

V1 pode ser configurada por templates internos. Um builder visual estilo Zapier não é necessário no primeiro momento.

---

# 15. Agenda e reuniões

## 15.1. Objetivo

Permitir que o SDR agende sem sair do contexto do lead.

## 15.2. Fluxo

Durante a conversa:

1. abrir disponibilidade;
2. selecionar horário;
3. confirmar duração;
4. adicionar prospect;
5. criar videoconferência quando aplicável;
6. salvar;
7. atualizar oportunidade;
8. iniciar workflow de confirmação/lembrete.

## 15.3. Estratégia

O Bioma oferece a UX e contexto comercial. O calendário externo continua como infraestrutura de agenda e sincronização.

---

# 16. WhatsApp e lembretes

## 16.1. Casos de uso

- mensagem após tentativa sem atendimento;
- confirmação de reunião;
- lembrete pré-reunião;
- follow-up;
- mensagem contextual depois de uma conversa;
- envio de material aprovado.

## 16.2. Princípio

O Bioma deve usar uma integração oficial/adequada para o canal e respeitar regras vigentes de consentimento, templates, janelas de conversa e uso comercial.

## 16.3. Conteúdo personalizado

O sistema pode escolher templates e preencher dados do prospect, reunião e vendedor.

Áudios pré-gravados podem ser considerados como um formato de conteúdo, mas a experiência não deve ser desenhada para enganar o destinatário sobre a natureza automatizada do envio.

## 16.4. Estados necessários

- queued;
- sent;
- delivered;
- read quando disponível;
- failed;
- replied.

Esses estados devem alimentar a timeline da oportunidade.

---

# 17. Sales Coach e IA contextual

## 17.1. Função

O Coach atende situações que não cabem perfeitamente em um card determinístico.

## 17.2. Contexto utilizado

- Account;
- Person;
- Opportunity;
- motion;
- stage;
- histórico;
- lista/origem;
- transcript quando disponível;
- Sales Knowledge publicado;
- cases relevantes;
- guardrails.

## 17.3. Saída estruturada

Idealmente:

```text
Interpretação
Objetivo
Pergunta recomendada
Por quê
Risco/atenção
Cards relacionados
Confiança
```

## 17.4. Regra

A IA não deve inventar cases, métricas, preços ou capacidades técnicas.

---

# 18. Pre-call e briefing automático

Antes de uma reunião qualificada, o Bioma pode preparar:

- resumo da empresa;
- contatos e papéis;
- origem da oportunidade;
- problema identificado;
- principais falas do prospect;
- motion provável;
- histórico de interações;
- objeções anteriores;
- perguntas ainda não respondidas;
- cases aplicáveis;
- riscos;
- próximo objetivo comercial.

Isso aproveita diretamente o Commercial Core + Sales Knowledge.

---

# 19. Handoff SDR → Closer

O handoff deve ser uma operação estruturada.

## Campos mínimos sugeridos

- empresa;
- contato;
- cargo;
- problema;
- situação atual;
- impacto;
- prioridade;
- tentativas anteriores;
- motion provável;
- participantes da decisão conhecidos;
- objeções relevantes;
- próximo passo;
- meeting link/data.

O Bioma pode avisar quando informações importantes ainda não foram levantadas, sem impedir rigidamente a operação quando o contexto justificar.

---

# 20. Home / Today

A home de Sales não deve abrir em um Kanban.

Exemplo de blocos:

## Today

- tasks vencendo;
- follow-ups;
- respostas novas;
- reuniões;
- leads prioritários;
- prospecting session planejada.

## Focus

Opportunities/leads que precisam de ação e por quê.

## Quick actions

- Find Leads;
- Start Prospecting Session;
- Follow-up;
- Search Playbook;
- Prepare Call;
- Schedule Meeting.

## Intelligence

- oportunidades em risco;
- leads sem atividade;
- cards recomendadas;
- gaps de informação.

---

# 21. Busca global e Command Palette

Atalho sugerido: `Ctrl/Cmd + K`.

Permitir buscas como:

- “cliente já tem agência”;
- “como perguntar budget”;
- “follow-up sem resposta”;
- “leads dentistas Florianópolis”;
- “abrir ACME”;
- “tarefas hoje”.

Resultados podem misturar:

- cards;
- Accounts;
- People;
- Opportunities;
- Tasks;
- Lists;
- actions.

---

# 22. Analytics e aprendizagem

## 22.1. Funnel operacional

- prospects importados;
- tentativas;
- conexões;
- conversas;
- qualificados;
- reuniões;
- oportunidades;
- propostas;
- ganhos.

## 22.2. List intelligence

Comparar por:

- fonte;
- segmento;
- localização;
- rating/reviews;
- filtros;
- campanha;
- período.

## 22.3. Prospecting Session

- calls/hour;
- connection rate;
- conversation rate;
- meeting rate;
- follow-up rate;
- invalid rate.

## 22.4. Sales Knowledge

- cards mais consultadas;
- buscas sem resultado;
- helpful/not helpful;
- cards abertas durante calls;
- objeções recorrentes;
- conteúdos desatualizados.

## 22.5. Coaching

- perguntas importantes não feitas;
- padrões de objeção;
- handoffs incompletos;
- progressão por SDR;
- roleplays recomendados.

---

# 23. Knowledge feedback loop

Fluxo desejado:

```text
Operação real
↓
Nova situação / objeção
↓
Busca ou Coach
↓
Decisão do SDR
↓
Resultado
↓
Telemetria / feedback
↓
Atualização do Sales Knowledge
↓
Treinamento / operação melhor
```

Exemplo futuro:

> “A objeção ‘nosso ERP já faz isso’ apareceu 14 vezes nas últimas 3 semanas e não existe card VALIDATED para o cenário.”

O Bioma pode sugerir revisão/criação de conteúdo para um gestor.

---

# 24. O que deve ser nativo vs. integrado

| Capability | Bioma possui | Provider externo |
|---|---|---|
| Busca em linguagem natural | Sim | — |
| Critérios e filtros | Sim | — |
| Lead Lists | Sim | — |
| Scraping bruto | Não necessariamente | Apify/outros |
| Normalização/dedupe | Sim | — |
| Account/Person/Opportunity | Sim | — |
| Pipeline | Sim | — |
| Tasks/Activities | Sim | — |
| Prospecting Sessions | Sim | — |
| Call Queue | Sim | — |
| Telefonia/PSTN | Não | Provider Voice |
| Dispositions | Sim | — |
| Workflow Engine | Sim | — |
| Playbooks/Knowledge | Sim | — |
| Coach | Sim | LLM como infraestrutura |
| Calendar UX | Sim | Google/Outlook etc. |
| WhatsApp workflow | Sim | API/BSP |
| E-mail workflow | Sim | Provider/conta conectada |
| Analytics | Sim | — |

---

# 25. Complexidade das funcionalidades discutidas

Escala: 1 = simples; 5 = alta complexidade operacional/técnica.

| Funcionalidade | MVP | Produção robusta | Observação |
|---|---:|---:|---|
| Google Maps/Lead Scraper integrado | 2/5 | 3/5 | Fonte pode ser externa; valor está em filtros, dedupe e importação |
| CRM/Pipeline automático | 2/5 | 3/5 | Fundamental e alinhado ao Commercial Core |
| Prospecting Lists/Sessions | 2/5 | 3/5 | Alto valor operacional, boa relação esforço/impacto |
| Call Queue sem telefonia | 2/5 | 2.5/5 | Pode ser entregue cedo |
| Power Dialer | 4/5 | 4.5/5 | Principal bloco de infraestrutura especializada |
| Dispositions | 1.5/5 | 2/5 | Simples isoladamente |
| Workflow Engine | 2.5/5 | 3.5/5 | Cresce conforme flexibilidade exigida |
| Calendar Scheduling | 2/5 | 3/5 | Integrar, não reconstruir calendário |
| WhatsApp + reminders | 3/5 | 4/5 | Regras do canal e confiabilidade aumentam complexidade |
| Sales Knowledge/Playbooks | 2/5 | 3/5 | Complexidade maior é editorial/governança, não técnica |
| Learn/Onboarding | 2.5/5 | 3.5/5 | Reusar a mesma base de conhecimento |
| AI Coach | 3/5 | 4/5 | Qualidade depende de grounding, guardrails e contexto |
| Analytics/Insights | 2.5/5 | 4/5 | Começa simples e amadurece com volume de dados |

---

# 26. Priorização por valor x complexidade

## Prioridade muito alta

- Commercial Core;
- Lead Lists;
- Google Maps Scraper integration;
- normalização/deduplicação;
- Prospecting Sessions;
- Call Queue;
- Dispositions;
- Tasks/follow-ups;
- Workflow templates;
- Sales Knowledge;
- onboarding básico;
- Calendar integration.

## Prioridade alta após core

- WhatsApp oficial;
- Coach contextual;
- pre-call briefing;
- automated handoff;
- list intelligence;
- content analytics.

## Prioridade posterior

- Power Dialer;
- live transcript suggestions mais sofisticadas;
- automations builder visual;
- scoring preditivo;
- análise avançada de calls;
- gamificação;
- predictive dialer.

---

# 27. MVP recomendado

A recomendação não é esperar o produto inteiro para gerar valor.

## MVP 1 — Prospecting Workspace

### Entregáveis

- Find Leads;
- integração do scraper já em desenvolvimento;
- Lead Lists;
- preview/import;
- normalização/dedupe;
- Accounts/People;
- pipeline básico;
- tasks;
- Call Queue manual;
- dispositions;
- Prospecting Sessions;
- playbook search;
- Sales Content inicial.

### Resultado

Um SDR já consegue trabalhar dentro do Bioma mesmo que a ligação ainda seja feita externamente.

---

# 28. MVP 2 — Automation & Meetings

### Entregáveis

- workflow templates;
- retries automáticos;
- follow-up scheduling;
- stage automation;
- Calendar integration;
- meeting handoff;
- confirmações/lembretes compatíveis com os canais conectados;
- Today/Home operacional.

### Resultado

Redução significativa do administrativo pós-contato.

---

# 29. MVP 3 — Communications

### Entregáveis

- WhatsApp integrado;
- timeline unificada;
- templates;
- estados de entrega;
- power dialer/voice provider;
- softphone;
- call states;
- disposição → próxima ligação.

### Resultado

O Bioma passa a controlar quase toda a sessão de prospecção em uma única experiência.

---

# 30. MVP 4 — Intelligence

### Entregáveis

- AI Coach;
- pre-call brief;
- next best action;
- recommendations;
- call analysis;
- knowledge gaps;
- lead/list performance;
- playbook effectiveness;
- onboarding adaptativo.

### Resultado

O produto deixa de ser apenas uma ferramenta de execução e passa a se tornar uma camada de inteligência comercial.

---

# 31. Roadmap sugerido

## Fase 0 — Fundação

- modelo de dados;
- taxonomy;
- permissions;
- activity timeline;
- provider interfaces;
- event model.

## Fase 1 — Prospecting Core

- scraper integration;
- lists;
- imports;
- normalization;
- dedupe;
- Accounts/People.

## Fase 2 — Execution Core

- opportunities;
- pipeline;
- tasks;
- Call Queue;
- dispositions;
- Prospecting Sessions.

## Fase 3 — Sales Knowledge

- cards;
- motions;
- ICPs;
- objections;
- playbooks;
- search;
- favorites;
- feedback;
- onboarding inicial.

## Fase 4 — Workflow & Calendar

- workflow templates;
- retries;
- follow-up;
- meeting scheduling;
- handoff.

## Fase 5 — Communications

- WhatsApp;
- e-mail timeline;
- voice/dialer;
- unified conversations.

## Fase 6 — Intelligence

- Coach;
- next best action;
- pre-call;
- analytics;
- knowledge health;
- coaching.

---

# 32. Eventos e telemetria mínimos

## Prospecting

- lead_search_created;
- lead_search_completed;
- lead_imported;
- lead_rejected;
- lead_deduplicated;
- list_created.

## Session

- prospecting_session_started;
- prospecting_session_paused;
- prospecting_session_completed.

## Calls

- call_attempt_created;
- call_connected;
- call_finished;
- call_disposition_set.

## Knowledge

- sales_card_viewed;
- sales_search_performed;
- sales_search_zero_results;
- sales_card_helpful;
- sales_card_not_helpful;
- coach_requested.

## Funnel

- opportunity_created;
- stage_changed;
- meeting_created;
- opportunity_qualified;
- opportunity_lost;
- opportunity_won.

---

# 33. Permissões iniciais

## SDR

- operar leads próprios;
- prospecting sessions;
- tasks;
- calls;
- playbooks;
- meeting scheduling;
- feedback de conteúdo.

## Closer

Tudo do SDR, mais:

- oportunidades avançadas;
- propostas;
- negociação;
- meeting outcome.

## Manager

- listas;
- assignments;
- workflows;
- content publishing;
- analytics;
- pipeline configuration.

## Admin

- providers;
- integrations;
- permissions;
- taxonomy;
- global configuration.

---

# 34. Riscos e cuidados

## 34.1. Construir CRM demais

Risco: tentar competir feature a feature com ferramentas maduras antes de validar o fluxo interno.

Mitigação: Commercial Core opinionated e focado no processo da EverGreen/Bioma.

## 34.2. Hardcode de automações

Risco: cada nova regra exigir alteração de código em vários pontos.

Mitigação: event model + workflow engine simples desde cedo.

## 34.3. Base de conhecimento morta

Risco: playbooks virarem documentação esquecida.

Mitigação: busca contextual, Call Mode, feedback, analytics e revisão por uso.

## 34.4. IA sem grounding

Risco: scripts inventados, promessas inadequadas ou recomendações inconsistentes.

Mitigação: conhecimento publicado, output estruturado e guardrails.

## 34.5. Canais externos

Risco: mudanças de API, regras de uso, consentimento, bloqueios ou custos.

Mitigação: provider adapters, monitoramento e revisão de conformidade vigente antes de cada integração.

## 34.6. Scraping e dados pessoais

Risco: uso inadequado de dados, armazenamento excessivo ou processo de prospecção incompatível com requisitos legais/contratuais.

Mitigação: minimização de dados, registro de origem, retenção definida, opt-out/bloqueio e validação jurídica/compliance para a operação final.

---

# 35. Como medir se o produto está funcionando

O sucesso não deve ser medido apenas por “features entregues”.

## Eficiência operacional

- menos tempo entre leads;
- menos atualizações manuais;
- mais chamadas/conversas por sessão;
- maior cumprimento de follow-ups.

## Qualidade comercial

- maior taxa de qualificação;
- maior show rate;
- melhores handoffs;
- menos reuniões sem fit;
- maior consistência entre SDRs.

## Conhecimento

- tempo para encontrar orientação;
- uso real de playbooks;
- buscas sem resultado;
- melhoria de cards baseada em evidência.

## Gestão

- visão clara da origem de reuniões/oportunidades;
- performance por lista;
- performance por motion;
- performance por SDR;
- identificação de gargalos.

---

# 36. Valor interno para a EverGreen

Mesmo que o Bioma Sales nunca seja vendido como produto isolado, o módulo pode gerar valor interno imediato:

- onboarding mais rápido de SDRs;
- processo comercial menos dependente dos fundadores;
- prospecção ativa mais previsível;
- dados centralizados;
- padronização de follow-up;
- melhoria de handoff;
- aprendizado com calls reais;
- experimentação de listas e abordagens;
- menor dependência de ferramentas fragmentadas.

---

# 37. Potencial de produto/SaaS

Se o fluxo interno funcionar, existe possibilidade de generalização para clientes.

A proposta não seria apenas “mais um CRM”.

O diferencial possível seria:

> **AI-native Sales Operating System para pequenas e médias operações comerciais, unindo geração de prospects, execução, conhecimento, automação e inteligência.**

Possíveis segmentos futuros:

- agências;
- consultorias;
- software houses;
- empresas B2B de serviço;
- operações locais com outbound;
- equipes comerciais pequenas que não querem administrar múltiplas ferramentas.

Essa hipótese deve ser validada somente depois que a própria EverGreen usar o sistema e gerar evidência operacional.

---

# 38. Não objetivos da primeira versão

Não construir agora:

- CRM enterprise genérico;
- marketing automation completo;
- inbox omnichannel completo;
- predictive dialer;
- plataforma de call center;
- scraping engine próprio para todas as fontes;
- LMS completo;
- construtor visual de automações extremamente flexível;
- lead scoring ML sofisticado;
- autonomia total de IA sobre contatos externos.

---

# 39. Decisão recomendada

O conjunto discutido faz sentido para o Bioma porque as funcionalidades não são apenas adjacentes: elas formam um único ciclo operacional.

```text
ENCONTRAR
↓
QUALIFICAR
↓
ORGANIZAR
↓
CONTATAR
↓
CONVERSAR
↓
DECIDIR
↓
AUTOMATIZAR
↓
AGENDAR
↓
APRENDER
↓
MELHORAR A PRÓXIMA PROSPECÇÃO
```

A melhor estratégia é construir esse ciclo em camadas, começando por **Prospecting + Commercial Core + Sales Knowledge + Execution**, e adicionar Communications/Intelligence depois que o fluxo central estiver sendo utilizado.

---

# 40. Próximos artefatos recomendados

A partir deste documento, os próximos artefatos técnicos devem ser:

1. **Functional Requirements Spec** — requisitos por tela e fluxo;
2. **Data Model Spec** — entidades, campos, estados e relações;
3. **Event & Workflow Spec** — triggers, actions e regras;
4. **Sales Content Spec** — já iniciada, com cards editoriais reais;
5. **UX Flow / Wireframes** — Find Leads, Session, Call, Disposition, Today e Knowledge;
6. **Integration Spec** — scraper, Calendar, WhatsApp e Voice;
7. **MVP Backlog** — épicos, histórias, dependências e critérios de aceite.

---

# 41. Síntese

O Bioma Sales & Prospecting não deve nascer como uma coleção de features soltas.

O produto deve conectar três coisas que normalmente ficam separadas:

**dados comerciais + conhecimento comercial + execução.**

O Google Maps Scraper é uma excelente porta de entrada, porque resolve o início da jornada. O valor maior aparece quando o lead deixa de ser apenas uma linha raspada e passa a entrar em um sistema que sabe:

- de onde ele veio;
- por que ele foi selecionado;
- quem deve abordá-lo;
- o que perguntar;
- qual playbook usar;
- qual foi o resultado;
- quando retomar;
- quando escalar;
- e o que a operação aprendeu com tudo isso.

Essa é a visão proposta para a evolução do domínio Sales dentro do Bioma.
