-- SEC-003 (continuação): rate limit de login fora da memória do processo.
--
-- O limite vivia num dict de processo (`routers/auth.py`), então: zerava a
-- cada deploy/restart e não valia nada com duas réplicas — cada uma contava
-- as suas próprias tentativas, multiplicando o limite efetivo pelo número de
-- instâncias. Persistir em Postgres resolve os dois casos sem introduzir
-- Redis, e a fila do worker já provou que Postgres basta nesta escala.
--
-- LGPD: a chave é `sha256(ip:email)`, nunca o par em texto. O limite continua
-- funcionando (o hash é determinístico) sem transformar a tabela num registro
-- persistente de quem tentou entrar de onde. `scripts/cleanup.py` apaga o que
-- saiu da janela.

create table if not exists login_attempts (
  id uuid primary key default gen_random_uuid(),
  key_hash text not null,
  attempted_at timestamptz not null default now()
);

create index if not exists login_attempts_key_time_idx
  on login_attempts (key_hash, attempted_at desc);

create index if not exists login_attempts_attempted_at_idx
  on login_attempts (attempted_at);
