-- AUTH-003: login social como VÍNCULO (decisão 2026-07-16): a conta do Bioma
-- continua sendo o usuário convidado pela EG; o Google é uma identidade
-- linkável/deslinkável para facilitar o login — nunca a "dona" da conta.

create table if not exists identities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  provider text not null check (provider in ('google')),
  provider_subject text not null,
  email text,
  created_at timestamptz not null default now(),
  unique (provider, provider_subject)
);

create index if not exists identities_user_idx on identities (user_id);
