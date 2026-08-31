create table if not exists leads (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  name text not null,
  company text,
  role_title text,
  email text,
  phone text,
  linkedin_url text,
  source text,
  stage text not null default 'new' check (stage in ('new', 'qualifying', 'meeting', 'proposal', 'won', 'lost')),
  expected_value numeric(12, 2),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists leads_org_stage_idx on leads (organization_id, stage);

create table if not exists financial_records (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  kind text not null check (kind in ('contract', 'invoice')),
  title text not null,
  amount numeric(12, 2),
  currency text not null default 'BRL',
  status text not null default 'open' check (status in ('draft', 'open', 'paid', 'overdue', 'cancelled')),
  contract_start_at date,
  contract_end_at date,
  due_at date,
  paid_at date,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists financial_records_org_status_idx on financial_records (organization_id, status);

create table if not exists performance_metrics (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  period_start date not null,
  period_end date not null,
  channel text not null,
  metric text not null,
  value numeric(14, 2) not null,
  source text not null default 'manual',
  notes text,
  captured_at timestamptz not null default now()
);

create index if not exists performance_metrics_org_period_idx on performance_metrics (organization_id, period_start, period_end);
