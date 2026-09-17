-- Sessões passam a saber DE ONDE vieram e QUANDO foram usadas.
--
-- Sintoma relatado: a tela "navegadores e dispositivos autorizados" mostrava
-- centenas de linhas idênticas ("Navegador / Dispositivo Web", todas com o
-- mesmo horário). Não era erro de renderização — a tabela não guardava nada
-- que distinguisse uma sessão da outra, então a tela não tinha o que mostrar.
--
-- Duas causas somadas:
--   1. cada login insere uma linha nova e nada nunca reaproveita;
--   2. `cleanup.py` só apaga sessão EXPIRADA há 7+ dias, e a renovação
--      rolante estende a validade de qualquer sessão em uso — então uma
--      sessão ativa nunca expira e nunca é limpa. Somado aos logins dos
--      smokes (cada um faz 2-3 logins como o admin, 40 smokes por rodada),
--      chegou a 1006 sessões ativas para um usuário só.
--
-- `user_agent` resolve os dois: dá identidade à linha na tela E permite
-- distinguir sessão de teste (TestClient manda `testclient`) de sessão de
-- gente, que é o que a faxina dos smokes precisa para limpar sem risco.
--
-- `last_seen_at` é o que permite expirar por desuso em vez de só por prazo:
-- sem ele, "esta sessão ainda é usada?" não tem resposta no banco.

alter table sessions
  add column if not exists user_agent text,
  add column if not exists last_seen_at timestamptz;

-- Sessões antigas nunca tiveram registro de uso; adotar o momento da criação
-- é a estimativa honesta (não inventa atividade que não sabemos ter ocorrido).
update sessions set last_seen_at = created_at where last_seen_at is null;

create index if not exists sessions_user_last_seen_idx
  on sessions (user_id, last_seen_at desc);
