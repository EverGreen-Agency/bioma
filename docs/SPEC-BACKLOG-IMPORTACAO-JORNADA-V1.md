# Spec — Backlog, importação documental e jornada comercial v1

Status: implementado e validado localmente em 30/08/2026.

## 1. Objetivo

Transformar documentos, conversas e decisões em uma cadeia rastreável sem duplicar a função do módulo de tarefas:

```text
documento/reunião -> prévia com evidências -> backlog -> tarefa -> teste/evidência
```

O Work Graph guarda intenção e rastreabilidade. `eg_tasks` guarda execução. Uma user story só vira tarefa após confirmação humana explícita.

## 2. Backlog canônico

`work_items` suporta `story`, `milestone` e `opportunity_event`, além dos artefatos já existentes. Os campos operacionais são:

- estado: candidato, backlog, pronto, em andamento, concluído ou descartado;
- prioridade, rank e story points;
- contexto, critérios de aceitação e Definition of Done;
- início e fim planejados;
- documento de origem e tarefa materializada.

A materialização é idempotente: repetir a confirmação devolve a mesma tarefa. O vínculo `work_item materializes task` preserva a origem no Work Graph.

## 3. Importação de HTML

O endpoint recebe HTML de até 2 MB e nunca renderiza ou executa scripts. O parser v1 extrai, de forma determinística:

- cards com prioridade, tipo, timing, deadline, descrição, ação, trade-off e fonte;
- linha do tempo com intervalos, meses, trimestres e datas exatas;
- título e texto sanitizado para auditoria.

O resultado é uma `project_document_import` em estado `draft`. A pessoa revisa os candidatos, escolhe quais entram e decide se quer somente backlog ou backlog mais tarefas. O HTML do EatControl usado como referência gerou localmente 21 oportunidades/eventos e 14 marcos; itens sem data exata permanecem sem prazo e recebem aviso de revisão.

## 4. Jornada do Sales Copilot

Ao concluir uma sessão, o Copiloto grava um snapshot com:

- funil: aquisição, captação, diagnóstico, conversão e pós-venda;
- jornada 5 A's: Aware, Appeal, Ask, Act e Advocate;
- gargalo atual, próximas ações e referências de evidência;
- modo de geração e vínculo com cliente, oportunidade e proposta.

Scores não são inventados. Enquanto o Raio-X comercial não fornecer medidas, eles permanecem nulos. Quando há workspace e ainda não há oportunidade, a sessão propõe `opportunity_registration`; somente a confirmação humana cria o registro comercial.

## 5. User stories cobertas

1. Como operador, quero registrar user stories com critérios, DoD e datas para organizar produto e projeto antes de criar tarefas.
2. Como operador, quero transformar uma story aprovada em tarefa sem perder sua origem e sem criar duplicatas.
3. Como responsável por projeto, quero enviar um HTML e revisar eventos, ações e cronograma extraídos antes de incorporá-los ao backlog.
4. Como responsável pelo EatControl, quero ver deadlines e marcos do documento na mesma fonte de planejamento do projeto.
5. Como vendedor, quero concluir uma reunião e obter o funil e a jornada atuais com gargalo, evidências e próximos passos.
6. Como gestor, quero registrar a oportunidade identificada na reunião apenas depois de revisar e confirmar a proposta do agente.

## 6. Definition of Done desta versão

- migração 0107 aplicável após 0001–0106 em PostgreSQL 16 limpo;
- parser coberto por testes com deadline, ação, trade-off e timeline;
- API com preview, listagem, materialização HITL e replay idempotente;
- UI com backlog gerenciável, importação/revisão e criação de tarefas;
- sessão comercial expondo mapa do funil, 5 A's, gargalo e ações;
- OpenAPI e tipos TypeScript sincronizados;
- testes de API, testes web e build de produção aprovados.

## 7. Limites reais

- o parser v1 reconhece HTML estruturado; documentos arbitrários podem exigir revisão manual ou uma futura extração semântica por provedor;
- monitoramento proativo de eventos ainda exige uma fonte web/agenda conectada;
- Google Meet e Teams aceitam ingestão por adaptador, mas o Bioma não entra sozinho em reuniões sem um provedor de bot/transcrição autorizado;
- a validação local não prova operação diária, segurança em produção ou entrega de mensagens por WhatsApp.
