-- INT-CU-RETIRE-001: remove os últimos vestígios do adapter ClickUp do schema.
-- Os 48 deliverables importados já foram religados a projetos nativos
-- "Legado ClickUp (pré-migração)" (ver bioma/docs/clickup-legacy-reconciliation-2026-07-24.json)
-- antes desta migration rodar, então nenhuma referência é perdida.

alter table deliverables drop column if exists clickup_task_id;
alter table clients drop column if exists clickup_folder_id;
drop table if exists clickup_mappings;
