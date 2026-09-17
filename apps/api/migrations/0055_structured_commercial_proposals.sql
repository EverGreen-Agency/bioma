-- Propostas comerciais ligadas ao cliente canônico, com briefing e versão preservados.
alter table commercial_proposals
  add column if not exists workspace_id uuid references workspaces(id) on delete set null,
  add column if not exists series_id uuid not null default gen_random_uuid(),
  add column if not exists version integer not null default 1,
  add column if not exists title text,
  add column if not exists proposal_type text,
  add column if not exists contractor_name text,
  add column if not exists team_members jsonb not null default '[]'::jsonb,
  add column if not exists delivery_modality text,
  add column if not exists selected_services jsonb not null default '[]'::jsonb,
  add column if not exists special_requirements text,
  add column if not exists estimated_budget text,
  add column if not exists payment_terms text,
  add column if not exists urgency text,
  add column if not exists decision_maker text,
  add column if not exists problem_summary text,
  add column if not exists additional_context text,
  add column if not exists intake_snapshot jsonb not null default '{}'::jsonb;

update commercial_proposals
set title = coalesce(nullif(client_name, ''), 'Proposta comercial')
where title is null;

alter table commercial_proposals
  alter column title set not null;

alter table commercial_proposals
  drop constraint if exists commercial_proposals_status_check,
  drop constraint if exists commercial_proposals_version_check,
  drop constraint if exists commercial_proposals_team_members_check,
  drop constraint if exists commercial_proposals_selected_services_check,
  drop constraint if exists commercial_proposals_intake_snapshot_check;

alter table commercial_proposals
  add constraint commercial_proposals_status_check
    check (status in ('draft', 'approved', 'sent', 'negotiating', 'won', 'lost')),
  add constraint commercial_proposals_version_check check (version > 0),
  add constraint commercial_proposals_team_members_check
    check (jsonb_typeof(team_members) = 'array'),
  add constraint commercial_proposals_selected_services_check
    check (jsonb_typeof(selected_services) = 'array'),
  add constraint commercial_proposals_intake_snapshot_check
    check (jsonb_typeof(intake_snapshot) = 'object');

create index if not exists commercial_proposals_workspace_idx
  on commercial_proposals (workspace_id, updated_at desc);

create unique index if not exists commercial_proposals_series_version_idx
  on commercial_proposals (series_id, version);
