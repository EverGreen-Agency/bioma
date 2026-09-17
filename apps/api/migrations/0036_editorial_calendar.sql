-- Migration 0036: Calendário Editorial & Esteira de Produção Social Media

create table if not exists workspace_editorial_calendar (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  title text not null,
  content_type text not null default 'social_post' check (content_type in ('social_post', 'image_ad', 'video_script', 'article')),
  channel text not null default 'instagram' check (channel in ('instagram', 'facebook', 'linkedin', 'youtube', 'tiktok', 'blog')),
  scheduled_at timestamptz,
  stage text not null default 'ideation' check (stage in ('ideation', 'production', 'review', 'approved', 'scheduled', 'published')),
  post_text text,
  media_urls jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists workspace_editorial_calendar_workspace_idx
  on workspace_editorial_calendar (workspace_id, scheduled_at asc);

create index if not exists workspace_editorial_calendar_stage_idx
  on workspace_editorial_calendar (workspace_id, stage);
