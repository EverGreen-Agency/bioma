-- Portal EG do cliente: classificação de leads e captura de conversas do Kommo.
--
-- kommo_lead_classifications: o que o classificador decidiu para cada lead (campo,
-- valor, confiança, motor) e se gravou no Kommo. Não guarda o texto da conversa:
-- a conversa é relida do Kommo na hora de classificar.
--
-- kommo_webhooks: o webhook que o Bioma registrou no Kommo para ser avisado de
-- mensagem e lead novos. O segredo faz parte da URL de destino.

create table if not exists kommo_lead_classifications (
  organization_id uuid not null references organizations(id) on delete cascade,
  lead_id bigint not null,
  status text not null,
  engine text not null,
  messages_count int not null default 0,
  fields jsonb not null default '{}'::jsonb,
  fields_written int not null default 0,
  error text,
  trigger text not null default 'historico',
  classified_at timestamptz not null default now(),
  primary key (organization_id, lead_id)
);

create index if not exists kommo_lead_classifications_recent_idx
  on kommo_lead_classifications (organization_id, classified_at desc);

create table if not exists kommo_webhooks (
  organization_id uuid primary key references organizations(id) on delete cascade,
  secret text not null,
  kommo_webhook_id bigint,
  destination text not null,
  events text[] not null default '{}',
  last_event_at timestamptz,
  events_received int not null default 0,
  created_at timestamptz not null default now()
);
