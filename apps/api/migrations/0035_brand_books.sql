-- Migration 0035: Brand Book Versionado & Diretrizes Metodológicas de Marca

create table if not exists workspace_brand_books (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  version integer not null default 1,
  tom_de_voz text not null default 'Profissional, Autoridade, Direto e Orientado a Resultados',
  arquetipo text not null default 'O Governante / O Especialista',
  posicionamento text,
  proposta_valor text,
  regras_copy jsonb not null default '[]'::jsonb,
  paleta_cores jsonb not null default '[]'::jsonb,
  status text not null default 'active' check (status in ('active', 'draft', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, version)
);

create index if not exists workspace_brand_books_workspace_idx
  on workspace_brand_books (workspace_id, version desc);
