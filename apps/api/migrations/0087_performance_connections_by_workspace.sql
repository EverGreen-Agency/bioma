-- Conexão de performance passa a pertencer ao WORKSPACE, não ao cliente.
--
-- **Isto termina um trabalho começado na 0013**, não começa um novo. Aquela
-- migração já acrescentou `workspace_id` a `performance_connections` (num
-- laço sobre 18 tabelas, o que o torna difícil de achar por busca) e já fez
-- o backfill com esta mesma junção. O que ela NÃO fez, e por isso o assunto
-- voltou:
--
--   * `workspace_id` ficou NULÁVEL — existia, mas nada garantia que estivesse
--     preenchido, então nenhum código podia confiar nele;
--   * `client_id` continuou NOT NULL — e é essa coluna que obrigava a EG a
--     ter um registro em `clients` ("EverGreen Internal") só para conseguir
--     conectar a própria mídia. A agência fingindo ser cliente de si mesma
--     para satisfazer uma restrição;
--   * a unicidade continuou sendo `(client_id, provider, external_account_id)`
--     — ou seja, o cliente seguia sendo a AUTORIDADE, mesmo com a coluna nova
--     ali do lado.
--
-- Resultado: metade da migração feita é pior que nenhuma, porque a coluna
-- presente sugere que o problema estava resolvido. Estava só começado.
--
-- Depois desta: Operação EG e hub de cliente são dois workspaces e conectam
-- contas de mídia pelo mesmo caminho. Nenhum registro-fantasma.
--
-- `client_id` fica (opcional) em vez de sair: as métricas diárias gravam os
-- dois e várias consultas de carteira agrupam por cliente. O que muda é quem
-- MANDA — passa a ser `workspace_id`.

-- Idempotente e no-op se a 0013 rodou; presente para esta migração se
-- sustentar sozinha em banco novo.
alter table performance_connections
  add column if not exists workspace_id uuid references workspaces(id) on delete cascade;

-- Rede de segurança: a 0013 já preencheu, mas uma linha inserida por código
-- entre as duas migrações pode ter escapado. Mesma junção que
-- `find_accessible_client` usa, então nenhuma conexão muda de dono.
update performance_connections pc
set workspace_id = w.id
from clients c
join workspaces w
  on w.subject_organization_id = c.organization_id
 and w.status = 'active'
where pc.client_id = c.id
  and pc.workspace_id is null;

-- Aqui está a mudança que importa. Sobrando linha sem workspace, a migração
-- falha em vez de deixar conexão órfã que some da tela sem explicação.
alter table performance_connections
  alter column workspace_id set not null;

-- E aqui a que dissolve o cliente-fantasma.
alter table performance_connections
  alter column client_id drop not null;

-- A unicidade passa a ser por workspace. A antiga (client_id, provider,
-- external_account_id) continuaria valendo para as linhas com cliente, mas
-- não protegeria a Operação EG, que agora pode ter conexão com `client_id`
-- nulo — e em Postgres NULL não colide com NULL, então a chave antiga
-- permitiria cadastrar a mesma conta do Google Ads da EG várias vezes.
alter table performance_connections
  drop constraint if exists performance_connections_client_id_provider_external_account_key;

create unique index if not exists performance_connections_workspace_account_idx
  on performance_connections (workspace_id, provider, external_account_id);

create index if not exists performance_connections_workspace_provider_idx
  on performance_connections (workspace_id, provider);
