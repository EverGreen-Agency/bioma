-- Remove credencial sem consumidor real, torna links públicos temporários e
-- registra se a proposta veio de execução live ou de prévia local explícita.
alter table opportunity_platform_configs
  drop column if exists api_key_or_token;

alter table commercial_proposals
  add column if not exists generation_mode varchar(20) not null default 'manual'
    check (generation_mode in ('live', 'preview', 'manual')),
  add column if not exists public_expires_at timestamptz not null
    default (now() + interval '30 days');

insert into opportunity_platform_configs (
  platform_key, platform_name, status, monthly_cost_cents, notes
)
values
  ('freelancer_br', 'Freelancer.com.br', 'active', 0, 'Feed RSS público'),
  ('weworkremotely', 'WeWorkRemotely', 'active', 0, 'Feeds RSS públicos'),
  ('remotive', 'Remotive', 'active', 0, 'Feed RSS público'),
  ('other', 'Outras fontes RSS', 'not_configured', 0, 'Exige URL RSS explícita')
on conflict (platform_key) do nothing;
