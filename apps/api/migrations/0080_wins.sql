-- Mural de vitórias: o que deu certo, registrado à mão ou detectado sozinho.
--
-- Por que existe: o Bioma sabe de tudo que está atrasado, bloqueado e em risco —
-- e de nada que deu certo. Operação que só enxerga problema desgasta quem
-- trabalha nela. Vitória some no dia seguinte se ninguém escreve.
--
-- Duas origens, e a diferença importa:
--
-- - `manual`: alguém digitou. "Conta aprovada na plataforma X" não está em
--   tabela nenhuma, e forçar isso a virar dado estruturado só faria ninguém
--   registrar.
-- - `automatic`: um detector viu no banco. Carrega a evidência (que linha
--   disparou) e uma chave de dedupe, porque detector que roda de hora em hora
--   não pode transformar a mesma proposta ganha em 24 vitórias.
--
-- `benchmark_link` amarra ao Raio-X: quando a vitória vem de um número que
-- cruzou um limiar, guardamos qual. Assim "meta batida" não é uma frase — é um
-- número com origem.

create table if not exists wins (
  id uuid primary key default gen_random_uuid(),

  title text not null,
  description text,
  category text not null default 'operacao'
    check (category in ('comercial', 'operacao', 'produto', 'cliente', 'time', 'financeiro')),

  source text not null default 'manual' check (source in ('manual', 'automatic')),
  -- Qual detector disparou. Nulo quando manual.
  rule_key text,
  -- Impede a mesma vitória duas vezes. Para detectores é
  -- `<rule_key>:<id da linha>`; nulo em vitória manual, porque duas manuais
  -- iguais são duas comemorações e isso é legítimo.
  dedupe_key text unique,
  -- De onde veio: tabela, id e o que estava lá. Vitória automática sem
  -- evidência é indistinguível de vitória inventada.
  evidence jsonb not null default '{}'::jsonb,

  -- Número quando existe: "3" reuniões, "12000" reais. Nulo para o que não se
  -- mede — nem toda vitória tem métrica, e forçar uma produziria número falso.
  metric_value numeric,
  metric_unit text,
  -- Quando a vitória nasce de um indicador do Raio-X/benchmark cruzando um
  -- limiar, guarda qual: {"pillar": "demanda", "from": 42, "to": 68}.
  benchmark_link jsonb,

  workspace_id uuid references workspaces(id) on delete cascade,
  -- Vitória que é do CEO — decisão fechada, negociação virada, marco pessoal.
  -- É o recorte que vai para o Fóton.
  is_ceo boolean not null default false,
  -- Quem aparece na vitória. Array de user_id: uma entrega é do time.
  credited_user_ids jsonb not null default '[]'::jsonb,

  -- `client` só aparece no hub se alguém liberar de propósito.
  visibility text not null default 'eg' check (visibility in ('eg', 'client')),
  pinned boolean not null default false,
  -- Quem reagiu. jsonb e não tabela: é um "joinha", não um domínio.
  reactions jsonb not null default '{}'::jsonb,

  occurred_at timestamptz not null default now(),
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists wins_occurred_idx on wins (occurred_at desc);
create index if not exists wins_category_idx on wins (category, occurred_at desc);
create index if not exists wins_ceo_idx on wins (is_ceo, occurred_at desc) where is_ceo;
create index if not exists wins_workspace_idx on wins (workspace_id, occurred_at desc);

-- Última varredura de cada detector. Sem isto, o detector varreria a história
-- inteira toda vez — e a primeira execução despejaria anos de vitórias de uma
-- vez no mural, enterrando o que aconteceu hoje.
create table if not exists win_detector_runs (
  rule_key text primary key,
  last_scanned_at timestamptz not null default now(),
  last_found integer not null default 0,
  total_found integer not null default 0,
  updated_at timestamptz not null default now()
);
