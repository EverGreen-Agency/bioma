-- Migration 0060: Personal Access Tokens (acesso de app externo, ex: Fóton,
-- como o próprio usuário — mesmos direitos, sem cookie de sessão de navegador).

create table if not exists personal_access_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  name text not null,
  token_hash text not null unique,
  token_prefix text not null,
  last_used_at timestamptz,
  expires_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists personal_access_tokens_user_idx
  on personal_access_tokens (user_id);
