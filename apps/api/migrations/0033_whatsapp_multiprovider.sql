-- Migration 0033: WhatsApp Multi-provider Architecture (Evolution, Meta Cloud, Z-API, Custom)

create table if not exists workspace_whatsapp_providers (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  provider_type text not null check (provider_type in ('evolution', 'meta_cloud', 'zapi', 'custom')),
  api_url text,
  api_token text,
  instance_name text,
  phone_number text,
  status text not null default 'active' check (status in ('active', 'inactive', 'error')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, provider_type)
);

create table if not exists workspace_whatsapp_message_logs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  provider_type text not null,
  to_number text not null,
  message_type text not null default 'text' check (message_type in ('text', 'template', 'media')),
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'sent' check (status in ('queued', 'sent', 'delivered', 'read', 'failed')),
  error_message text,
  sent_at timestamptz not null default now()
);

create index if not exists workspace_whatsapp_logs_workspace_idx
  on workspace_whatsapp_message_logs (workspace_id, sent_at desc);
