with ranked as (
  select id,
    row_number() over (partition by account_id order by created_at desc, id desc) as position
  from ai_provider_login_sessions
  where status in ('pending', 'running', 'waiting_input')
)
update ai_provider_login_sessions session
set status = 'canceled',
  encrypted_pending_input = null,
  error_message = 'Substituída pela tentativa de login mais recente.',
  finished_at = now(),
  updated_at = now()
from ranked
where session.id = ranked.id and ranked.position > 1;

create unique index if not exists idx_ai_provider_login_sessions_one_active_per_account
  on ai_provider_login_sessions(account_id)
  where status in ('pending', 'running', 'waiting_input');

comment on index idx_ai_provider_login_sessions_one_active_per_account is
  'Impede duas sessões OAuth simultâneas de disputarem a mesma conta de provider.';
