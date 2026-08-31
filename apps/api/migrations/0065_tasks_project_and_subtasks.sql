-- Migration 0065: liga tarefas a projetos e cria subtarefa de verdade.
--
-- Contexto (Manual Operacional Bioma v2, 29/07/2026):
--
-- 1) PROJETO COMO CAMPO DA TAREFA
--    O Bioma já tinha `projects` como entidade completa (contratos, fases,
--    planos, documentos, integração GitHub) mas as tarefas em `eg_tasks` não
--    tinham nenhum vínculo com ela — dois mundos paralelos, herança da
--    aposentadoria do ClickUp. A decisão foi tornar projeto um CAMPO da tarefa
--    (não uma lista separada), porque frentes diferentes têm status diferentes
--    mas projetos da mesma frente compartilham a esteira (caso Univet: site,
--    app V1 e app V2 "passaram pelas mesmas fases").
--
--    É chave estrangeira, não texto: texto livre derivaria de nome
--    ("App V1"/"app v1"/"V1"), não alcançaria as datas de `project_phases`
--    necessárias para o Gantt, e perderia o vínculo com `project_contracts`.
--
-- 2) SUBTAREFA ≠ CHECKLIST
--    Distinção que existia na prática do time mas nunca foi documentada:
--      - Checklist  = etapas da MESMA tarefa (mesmo responsável, mesmo prazo).
--      - Subtarefa  = trabalho que trocou de mão: muda responsável OU prazo,
--                     tipicamente quando passa para outra área/equipe.
--    A tabela `eg_task_subtasks` (só title + is_completed) é, de fato, um
--    CHECKLIST — está correta nesse papel e permanece. Subtarefa de verdade
--    precisa de responsável, prazo e status próprios, logo é uma TAREFA COM
--    PAI, para aparecer no Kanban da equipe que assumiu, com o prazo dela.

alter table eg_tasks
  add column if not exists project_id uuid references projects(id) on delete set null,
  add column if not exists parent_task_id uuid references eg_tasks(id) on delete cascade;

-- Uma tarefa não pode ser pai de si mesma.
alter table eg_tasks
  drop constraint if exists eg_tasks_parent_not_self;
alter table eg_tasks
  add constraint eg_tasks_parent_not_self check (parent_task_id is null or parent_task_id <> id);

create index if not exists eg_tasks_project_idx on eg_tasks (project_id);
create index if not exists eg_tasks_parent_idx on eg_tasks (parent_task_id);

-- Documenta no próprio banco o que a tabela realmente é, já que o nome herdado
-- ("subtasks") diz o contrário e induziu ao erro antes.
comment on table eg_task_subtasks is
  'Itens de CHECKLIST de uma tarefa (etapas da mesma tarefa, sem responsavel/prazo proprios). Subtarefa de verdade e eg_tasks.parent_task_id. Ver Manual Operacional Bioma v2.';

comment on column eg_tasks.parent_task_id is
  'Tarefa-pai. Preenchido quando o trabalho trocou de responsavel ou de prazo (subtarefa). Para etapas internas sem troca de mao, use eg_task_subtasks (checklist).';

comment on column eg_tasks.project_id is
  'Projeto ao qual a tarefa pertence. Frente (eg_task_lists.type) define o vocabulario de status; projeto define escopo, contrato e datas do roadmap.';
