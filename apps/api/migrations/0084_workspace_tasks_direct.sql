-- 0084_workspace_tasks_direct.sql
-- Desacopla eg_tasks da eg_task_lists: toda tarefa passa a ter workspace_id
-- direto, e um campo discipline substitui o "tipo de lista" como filtro.
--
-- A eg_task_lists NÃO é dropada aqui — dados existentes continuam válidos e a
-- tabela pode ser removida em migração futura quando não houver mais referências
-- em produção. As novas tarefas criadas via POST /workspaces/{id}/tasks nunca
-- precisarão de list_id.

-- 1. Adiciona workspace_id direto em eg_tasks e torna list_id opcional
alter table eg_tasks
  add column if not exists workspace_id uuid references workspaces(id) on delete cascade;

alter table eg_tasks
  alter column list_id drop not null;


-- Backfill: tasks existentes herdam workspace_id da lista
update eg_tasks t
set workspace_id = l.workspace_id
from eg_task_lists l
where l.id = t.list_id
  and t.workspace_id is null;

-- Índice para queries por workspace
create index if not exists eg_tasks_workspace_idx on eg_tasks(workspace_id);

-- 2. Discipline: substitui o "tipo de lista" como filtro. Duas disciplinas
--    alinhadas com o Manual v2 (Growth e Tech). Social vive no Estúdio IA.
alter table eg_tasks
  add column if not exists discipline text check (discipline in ('growth', 'tech'));

-- Backfill: herda o tipo da lista como disciplina (exceto social/general)
update eg_tasks t
set discipline = case l.type
  when 'growth' then 'growth'
  when 'tech'   then 'tech'
  else null  -- social e general não mapeiam para uma disciplina nova
end
from eg_task_lists l
where l.id = t.list_id
  and t.discipline is null
  and l.type in ('growth', 'tech');

-- 3. Relaxa a constraint de tipo na eg_task_lists para não bloquear
--    (a coluna ainda existe por compat com dados antigos)
alter table eg_task_lists
  drop constraint if exists eg_task_lists_type_check;

alter table eg_task_lists
  add constraint eg_task_lists_type_check
    check (type in ('growth', 'tech', 'social', 'general'));

-- 4. Adiciona workspace_name na view de minhas tarefas (helper para o frontend)
--    A view list_my_tasks no repo já faz join com workspace, então nada muda lá.
