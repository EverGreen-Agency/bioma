-- Aceita o onboarding assistido e diferencia execução live, prévia e manual.
alter table workspace_squad_definitions
  drop constraint if exists workspace_squad_definitions_pilar_check;

alter table workspace_squad_definitions
  add constraint workspace_squad_definitions_pilar_check
    check (pilar in ('oferta', 'demanda', 'conversao', 'onboarding'));

alter table workspace_squad_executions
  drop constraint if exists workspace_squad_executions_pilar_check;

alter table workspace_squad_executions
  add constraint workspace_squad_executions_pilar_check
    check (pilar in ('oferta', 'demanda', 'conversao', 'onboarding')),
  add column if not exists generation_mode varchar(20) not null default 'manual'
    check (generation_mode in ('live', 'preview', 'manual'));
