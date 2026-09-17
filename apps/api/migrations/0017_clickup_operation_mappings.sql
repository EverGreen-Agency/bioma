-- INT-CU-002: classificação e tradução configurável por operação/lista.

alter table clickup_mappings
  add column if not exists operation text not null default 'general'
    check (operation in ('social', 'growth', 'tech', 'general'));

alter table clickup_mappings
  add column if not exists status_mapping jsonb not null default '{}'::jsonb;
