-- QUEUE-001: lease e tentativas para recuperar jobs presos em `running`.
--
-- Antes desta migration, `claim_next_sync`/`claim_next_ai_content` marcavam
-- `running` sem nenhum sinal de vida. Worker que morresse no meio (deploy,
-- OOM, queda de rede) deixava o job em `running` para sempre: nunca era
-- reprocessado, nunca virava erro e ainda bloqueava o reenfileiramento,
-- porque `enqueue_scheduled_syncs` ignora clientes com run em
-- `('queued','running')`. Um cliente parava de sincronizar em silêncio.
--
-- `heartbeat_at` é renovado no claim e durante o processamento; o reaper
-- devolve para `queued` o que passou do lease e ainda tem tentativa, e
-- encerra como `error` o que estourou o limite.

alter table sync_runs
  add column if not exists heartbeat_at timestamptz,
  add column if not exists attempts integer not null default 0;

alter table ai_content_requests
  add column if not exists heartbeat_at timestamptz,
  add column if not exists attempts integer not null default 0;

-- Runs já em `running` no momento da migration não têm heartbeat e ficariam
-- invisíveis para o reaper. Adotam started_at como marca inicial: se de fato
-- estiverem travados, o primeiro reaper os recupera.
update sync_runs
  set heartbeat_at = coalesce(heartbeat_at, started_at, now())
  where status = 'running' and heartbeat_at is null;

update ai_content_requests
  set heartbeat_at = coalesce(heartbeat_at, started_at, created_at, now())
  where status = 'running' and heartbeat_at is null;

-- Índices parciais: o reaper só varre linhas `running`.
create index if not exists sync_runs_running_heartbeat_idx
  on sync_runs (heartbeat_at)
  where status = 'running';

create index if not exists ai_content_requests_running_heartbeat_idx
  on ai_content_requests (heartbeat_at)
  where status = 'running';
