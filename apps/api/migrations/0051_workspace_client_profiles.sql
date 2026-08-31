-- Contexto operacional do cliente para onboarding e planejamento.
create table if not exists workspace_client_profiles (
  workspace_id uuid primary key references workspaces(id) on delete cascade,
  sector text,
  primary_offer text,
  initial_objective text,
  contact_email text,
  contact_phone text,
  website text,
  business_address text,
  business_details text,
  target_audience text,
  competitors text,
  marketing_objectives text,
  marketing_history text,
  challenges_opportunities text,
  resources_budget text,
  tone_of_voice text,
  preferences_restrictions text,
  created_by uuid references users(id) on delete set null,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists workspace_client_profiles_updated_idx
  on workspace_client_profiles (updated_at desc);
