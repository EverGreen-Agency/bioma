-- AI-CONTENT-001: primeiro fluxo vertical de conteúdo assistido por IA.

create table if not exists ai_content_requests (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  organization_id uuid not null references organizations(id) on delete cascade,
  requested_by uuid references users(id) on delete set null,
  content_type text not null default 'social_posts' check (content_type in ('social_posts')),
  status text not null default 'queued' check (status in ('queued', 'running', 'ready', 'error', 'cancelled')),
  brief text not null,
  channels jsonb not null default '[]'::jsonb,
  quantity integer not null default 3 check (quantity between 1 and 12),
  tone text,
  objective text,
  methodology_refs jsonb not null default '[]'::jsonb,
  provider text,
  model text,
  generation_mode text check (generation_mode in ('live', 'preview')),
  output jsonb,
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ai_content_requests_workspace_idx
  on ai_content_requests (workspace_id, created_at desc);

create index if not exists ai_content_requests_queue_idx
  on ai_content_requests (created_at)
  where status = 'queued';

alter table ai_runs add column if not exists workspace_id uuid references workspaces(id) on delete set null;
alter table ai_runs add column if not exists content_request_id uuid references ai_content_requests(id) on delete set null;
alter table ai_runs add column if not exists status text check (status in ('ok', 'error'));
alter table ai_runs add column if not exists metadata jsonb not null default '{}'::jsonb;
