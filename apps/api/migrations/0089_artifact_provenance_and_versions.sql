-- Artefatos do copiloto: procedência e versionamento (decisão 8).
--
-- O diagnóstico: `AiContentStudio` é um formulário. A conversa com o copiloto
-- produz um roteiro e ele MORRE no histórico — para reusar, copia-se e cola-se
-- em outro lugar. Enquanto isso o copiloto já tem thread, execução, fontes,
-- custo e cota. São dois sistemas paralelos que não se falam.
--
-- A decisão foi unificar via artefatos: a conversa gera uma peça, a peça fica
-- salva, versionada e navegável, e o Estúdio vira a VISTA dessas peças em vez
-- de um formulário concorrente.
--
-- **Estende `artifacts` em vez de criar tabela nova.** Ela existe desde a 0001
-- com exatamente a taxonomia aberta que o caso pede: `kind` é texto livre e
-- `visibility` já separa interno de cliente. Criar `copilot_artifacts` ao lado
-- produziria dois lugares para "material do cliente" e a pergunta "em qual dos
-- dois está?" para sempre.
--
-- O que faltava, e é só isto:
--
--   * PROCEDÊNCIA — de qual conversa e de qual execução a peça saiu. Sem isso
--     não dá para responder "com que informação isso foi escrito?", mesmo com
--     a trilha do copiloto guardando fontes, modelo e cota. O elo é que falta.
--   * VERSÃO — hoje `content` é sobrescrito. "Muda o gancho" apaga o gancho
--     anterior, e comparar v1 com v2 é impossível. Versão é o que transforma
--     regerar em iterar.
--   * WORKSPACE — `artifacts` só tem `organization_id`. Roteiro é de um
--     workspace, e sem isso a vista do Estúdio não consegue filtrar.
--   * STATUS — rascunho, aprovado, publicado. Sem isso tudo tem o mesmo peso
--     e a lista vira pilha.
--
-- Proposta e briefing NÃO viram artefato genérico: já têm casa própria
-- (`proposals`, com link público, ciclo de vida e tradução em cache). O
-- desenho é PROMOVER — a conversa gera o artefato e um botão o entrega para a
-- casa especializada quando ela existe. Rebaixar o que já é mais completo
-- seria perder função.

alter table artifacts
  add column if not exists workspace_id uuid references workspaces(id) on delete cascade;

-- `on delete set null` nos dois: apagar uma conversa não pode apagar o
-- material que ela produziu. O artefato sobrevive perdendo a origem — o
-- inverso destruiria trabalho.
alter table artifacts
  add column if not exists thread_id uuid references copilot_threads(id) on delete set null;

alter table artifacts
  add column if not exists run_id uuid references copilot_runs(id) on delete set null;

alter table artifacts
  add column if not exists status text not null default 'draft'
    check (status in ('draft', 'approved', 'published', 'archived'));

alter table artifacts
  add column if not exists current_version integer not null default 1 check (current_version > 0);

alter table artifacts
  add column if not exists updated_at timestamptz not null default now();

create index if not exists artifacts_workspace_idx on artifacts (workspace_id, created_at desc);
create index if not exists artifacts_thread_idx on artifacts (thread_id) where thread_id is not null;
create index if not exists artifacts_kind_idx on artifacts (organization_id, kind);

-- Histórico. `artifacts.content` continua sendo a versão CORRENTE (para não
-- quebrar as telas que já leem de lá); esta tabela guarda todas, inclusive a
-- corrente, para que comparar v1 com v2 seja uma consulta e não arqueologia.
create table if not exists artifact_versions (
  id uuid primary key default gen_random_uuid(),
  artifact_id uuid not null references artifacts(id) on delete cascade,
  version integer not null check (version > 0),

  title text not null,
  content text,
  url text,

  -- De qual execução saiu ESTA versão. Uma v2 pedida ao copiloto aponta o run
  -- que a gerou; uma v2 editada à mão fica nula, e a diferença entre as duas
  -- é exatamente o que se quer saber ao revisar.
  run_id uuid references copilot_runs(id) on delete set null,
  -- Por que mudou. Curto de propósito: "ajustei o gancho" vale mais que um
  -- diff que ninguém lê.
  change_note text,

  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),

  unique (artifact_id, version)
);

create index if not exists artifact_versions_artifact_idx
  on artifact_versions (artifact_id, version desc);

-- Backfill: todo artefato existente vira sua própria v1. Sem isto, um artefato
-- anterior a esta migração apareceria na tela como "sem histórico", o que é
-- diferente de "só tem uma versão" e faria a interface parecer quebrada.
insert into artifact_versions (artifact_id, version, title, content, url, created_by, created_at)
select a.id, 1, a.title, a.content, a.url, a.created_by, a.created_at
from artifacts a
where not exists (select 1 from artifact_versions v where v.artifact_id = a.id);
