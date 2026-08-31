-- Migration 0067: data de início da tarefa.
--
-- O manual v1 define a visão Gantt/Timeline como "baseado nas Datas Iniciais
-- e Datas de Vencimento" — mas eg_tasks só tinha due_date, então uma barra de
-- Gantt não tinha onde começar. start_date é opcional: tarefa sem início
-- definido vira um marco de um dia na data de vencimento.

alter table eg_tasks
  add column if not exists start_date timestamptz;

-- Início depois do fim é dado impossível; barrar no banco evita Gantt torto.
alter table eg_tasks
  drop constraint if exists eg_tasks_start_before_due;
alter table eg_tasks
  add constraint eg_tasks_start_before_due
  check (start_date is null or due_date is null or start_date <= due_date);
