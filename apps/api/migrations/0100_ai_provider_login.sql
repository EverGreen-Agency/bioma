create table if not exists ai_provider_credentials (
  account_id uuid primary key references ai_provider_accounts(id) on delete cascade,
  encrypted_bundle text not null,
  bundle_format text not null default 'bioma-json-v1',
  auth_method text,
  created_by uuid references users(id) on delete set null,
  updated_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table ai_provider_credentials is
  'Credenciais dos CLIs empacotadas e cifradas com SECRET_ENCRYPTION_KEY. Nunca retornadas pela API.';

create table if not exists ai_provider_login_sessions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  account_id uuid not null references ai_provider_accounts(id) on delete cascade,
  requested_by uuid references users(id) on delete set null,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'waiting_input', 'completed', 'failed', 'canceled', 'expired')),
  public_output text not null default '',
  prompt_hint text,
  encrypted_pending_input text,
  error_message text,
  expires_at timestamptz not null default (now() + interval '15 minutes'),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_ai_provider_login_sessions_account
  on ai_provider_login_sessions(account_id, created_at desc);

comment on table ai_provider_login_sessions is
  'Estado público do OAuth interativo. A entrada de uso único é cifrada e apagada assim que consumida.';
