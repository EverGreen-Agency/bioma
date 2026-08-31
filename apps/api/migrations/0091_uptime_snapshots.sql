-- Disponibilidade medida POR FORA, guardada aqui.
--
-- A regra que motiva a tabela inteira: uptime auto-medido não vale nada. Se o
-- Bioma medisse a si mesmo, uma queda total registraria 100% — quem mede caiu
-- junto. Por isso a medição vem de um prober externo (Better Stack) e esta
-- tabela é só o registro do que ele disse.
--
-- Por que guardar em vez de consultar a API na hora de desenhar a tela:
--
--   * a página de disponibilidade não pode depender de um terceiro estar no ar
--     (seria irônico e, pior, mostraria "sem dados" durante o incidente que ela
--     existe para relatar);
--   * o histórico passa a ser NOSSO. Trocar de provedor não apaga o passado —
--     os dias já coletados continuam aqui e o novo alimenta daí em diante.
--
-- `measured_since` é o que impede o número de mentir por omissão. Um monitor
-- criado hoje devolve "100% em 90 dias" — matematicamente correto e
-- comercialmente inútil. Guardando desde quando existe medição, a tela mostra
-- "medindo desde 08/08" até a janela encher, em vez de um número redondo sem
-- lastro.

create table if not exists uptime_snapshots (
  id uuid primary key default gen_random_uuid(),

  -- Identificação do monitor no provedor. `provider` fica explícito para o dia
  -- em que trocarmos: as linhas antigas continuam legíveis e atribuíveis.
  provider text not null default 'betterstack',
  monitor_id text not null,
  monitor_name text not null,
  -- `monitor` (URL) ou `heartbeat` (interruptor de homem morto do worker).
  kind text not null default 'monitor' check (kind in ('monitor', 'heartbeat')),

  -- Dia a que este retrato se refere (não o instante da coleta).
  snapshot_date date not null,
  -- Janela pedida ao provedor. 1 = o dia; 90 = a janela publicada.
  window_days integer not null check (window_days > 0),

  availability numeric(7, 4) not null check (availability >= 0 and availability <= 100),
  total_downtime_seconds integer not null default 0,
  number_of_incidents integer not null default 0,
  longest_incident_seconds integer not null default 0,
  average_incident_seconds integer not null default 0,

  -- Desde quando existe medição para este monitor. Sem isto, "100% em 90 dias"
  -- num monitor de um dia parece um resultado e é só falta de histórico.
  measured_since date,

  collected_at timestamptz not null default now(),

  unique (provider, monitor_id, snapshot_date, window_days)
);

create index if not exists uptime_snapshots_lookup_idx
  on uptime_snapshots (monitor_id, window_days, snapshot_date desc);
