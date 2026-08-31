-- AUTH-002: recuperação/rotação segura de senha por link de uso único,
-- no mesmo padrão dos convites (token hasheado, expiração curta).

create table if not exists password_resets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  used_at timestamptz,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists password_resets_user_created_idx on password_resets (user_id, created_at desc);
