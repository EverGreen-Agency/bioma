-- Rastreamento imutável da solicitação de IA (SHA-256 canônico)
alter table ai_execution_attempts
  add column if not exists request_hash varchar(64);

create index if not exists ai_execution_attempts_hash_idx
  on ai_execution_attempts (request_hash)
  where request_hash is not null;
