-- Decisão 14: publicar peça do Estúdio em CMS (WordPress primeiro).
--
-- Duas tabelas, e nenhuma delas guarda segredo: a credencial continua no cofre
-- (`vault_credentials`), cifrada pela API. `cms_targets` só aponta para ela.
-- Duplicar segredo aqui criaria um segundo lugar para rotacionar e um segundo
-- lugar para vazar.

create table if not exists cms_targets (
  id uuid primary key default gen_random_uuid(),
  tenant_organization_id uuid not null references organizations(id) on delete cascade,
  workspace_id uuid not null references workspaces(id) on delete cascade,

  label text not null,
  -- Aberto para crescer, fechado para o que existe hoje. WordPress primeiro,
  -- com os outros CMS no horizonte (decisão 14) — cada um entra com sua
  -- migração, porque cada um traz campo próprio.
  kind text not null default 'wordpress' check (kind in ('wordpress')),

  -- HTTPS obrigatório no banco, não só no código: Application Password viaja
  -- em Basic Auth, e sem TLS a senha vai em texto claro. Regra que protege
  -- segredo não pode depender de qual caminho de escrita foi usado.
  site_url text not null check (site_url like 'https://%'),

  credential_id uuid not null references vault_credentials(id) on delete restrict,

  -- Decisão 14, resposta do Eduardo: "ter como configurar as duas opções".
  -- O DEFAULT é rascunho, de propósito. Publicar por engano no site do cliente
  -- é o erro caro e difícil de desfazer; rascunho esquecido é o barato.
  publish_mode text not null default 'draft' check (publish_mode in ('draft', 'direct')),

  is_active boolean not null default true,

  last_checked_at timestamptz,
  last_check_error text,

  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  -- Um alvo por site por workspace. Dois registros para o mesmo site com modos
  -- diferentes tornariam "publica direto?" uma pergunta sem resposta.
  unique (workspace_id, site_url)
);

create index if not exists cms_targets_workspace_idx
  on cms_targets (workspace_id, is_active);


-- Onde cada VERSÃO da peça foi parar. Versão, não peça: a v1 pode estar no ar
-- enquanto a v3 é rascunho, e sem isso "esta peça está publicada?" não tem
-- resposta honesta.
create table if not exists artifact_publications (
  id uuid primary key default gen_random_uuid(),
  artifact_id uuid not null references artifacts(id) on delete cascade,
  version integer not null check (version > 0),
  target_id uuid not null references cms_targets(id) on delete cascade,

  -- Texto, não integer: o WordPress usa inteiro, mas outro CMS usa slug ou
  -- UUID, e migrar o tipo depois é pior que aceitar texto agora.
  external_id text not null,
  external_url text,
  -- Status COMO O CMS DEVOLVEU. Não é o que pedimos: o WordPress pode rebaixar
  -- para 'pending' conforme o papel do usuário, e registrar a intenção em vez
  -- do fato faria a tela mentir.
  external_status text,

  published_by uuid references users(id) on delete set null,
  published_at timestamptz not null default now(),

  -- Republicar a MESMA versão no MESMO alvo atualiza a linha em vez de criar
  -- outra: senão o histórico vira ruído e "onde está no ar?" fica ambíguo.
  unique (artifact_id, version, target_id)
);

create index if not exists artifact_publications_artifact_idx
  on artifact_publications (artifact_id, published_at desc);

create index if not exists artifact_publications_target_idx
  on artifact_publications (target_id, published_at desc);
