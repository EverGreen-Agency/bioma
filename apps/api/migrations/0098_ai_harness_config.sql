create table if not exists ai_harness_configs (
  organization_id uuid primary key references organizations(id) on delete cascade,
  planner_model_catalog_id uuid references ai_model_catalog(id) on delete set null,
  tool_caller_model_catalog_id uuid references ai_model_catalog(id) on delete set null,
  auditor_model_catalog_id uuid references ai_model_catalog(id) on delete set null,
  curator_model_catalog_id uuid references ai_model_catalog(id) on delete set null,
  enabled_tools text[] not null default array[]::text[],
  created_by uuid references users(id) on delete set null,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table ai_harness_configs is
  'Escolhas de modelo por papel do harness. Referencia catálogo, nunca credencial.';
