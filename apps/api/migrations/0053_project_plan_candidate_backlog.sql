-- Backlog candidato: IA sugere, equipe edita/seleciona e somente então aprova.
alter table project_plan_items
  add column if not exists selected boolean not null default true,
  add column if not exists priority text not null default 'medium',
  add column if not exists definition_of_done text,
  add column if not exists subtasks jsonb not null default '[]'::jsonb;

alter table project_plan_items
  drop constraint if exists project_plan_items_priority_check;

alter table project_plan_items
  add constraint project_plan_items_priority_check
    check (priority in ('low', 'medium', 'high', 'critical'));

alter table project_plan_items
  drop constraint if exists project_plan_items_subtasks_array_check;

alter table project_plan_items
  add constraint project_plan_items_subtasks_array_check
    check (jsonb_typeof(subtasks) = 'array');

create index if not exists project_plan_items_selected_idx
  on project_plan_items (plan_id, selected, sequence);
