-- Migration 0059: Content Intelligence — retrospectiva de conteúdo orgânico,
-- banco de ganchos e geração de roteiros mensais sem briefing manual.

create table if not exists workspace_content_retrospectives (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  period_start date not null,
  period_end date not null,
  posts_analyzed integer not null default 0,
  generation_mode text not null default 'preview',
  output_data jsonb not null default '{}'::jsonb,
  token_usage jsonb not null default '{}'::jsonb,
  estimated_cost_cents integer not null default 0,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists workspace_content_retrospectives_workspace_idx
  on workspace_content_retrospectives (workspace_id, created_at desc);

create table if not exists workspace_content_scripts (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  retrospective_id uuid references workspace_content_retrospectives(id) on delete set null,
  title text not null,
  theme text,
  hook_opening text,
  script_body text not null,
  suggested_format text,
  cta text,
  rationale text,
  status text not null default 'suggested'
    check (status in ('suggested', 'approved', 'scheduled', 'recorded', 'published', 'discarded')),
  scheduled_for date,
  generation_mode text not null default 'preview',
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists workspace_content_scripts_workspace_idx
  on workspace_content_scripts (workspace_id, created_at desc);
create index if not exists workspace_content_scripts_scheduled_idx
  on workspace_content_scripts (workspace_id, scheduled_for);

create table if not exists workspace_instagram_posts (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  client_id uuid references clients(id) on delete cascade,
  ig_media_id text not null,
  permalink text,
  media_type text not null,
  caption text,
  posted_at timestamptz,
  media_url text,
  thumbnail_url text,
  reach integer not null default 0,
  impressions integer not null default 0,
  likes integer not null default 0,
  comments integer not null default 0,
  shares integer not null default 0,
  saved integer not null default 0,
  plays integer not null default 0,
  avg_watch_time_seconds numeric,
  transcript text,
  transcript_generated_at timestamptz,
  source_script_id uuid references workspace_content_scripts(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, ig_media_id)
);

create index if not exists workspace_instagram_posts_workspace_date_idx
  on workspace_instagram_posts (workspace_id, posted_at desc);

create table if not exists workspace_content_hook_analyses (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  post_id uuid not null references workspace_instagram_posts(id) on delete cascade,
  source text not null check (source in ('llm_transcript', 'higgsfield_virality')),
  hook_text text,
  hook_pattern text,
  effectiveness_score numeric,
  analysis_notes text,
  raw_output jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (post_id, source)
);

create index if not exists workspace_content_hook_analyses_workspace_idx
  on workspace_content_hook_analyses (workspace_id, effectiveness_score desc);
