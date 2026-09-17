alter table ai_provider_accounts
  drop constraint if exists ai_provider_accounts_provider_check;

alter table ai_provider_accounts
  add constraint ai_provider_accounts_provider_check
  check (provider in ('openai', 'anthropic', 'google', 'openrouter', 'deepseek', 'groq'));

comment on column ai_provider_accounts.provider is
  'Fornecedor comercial. O canal/auth_mode diferencia assinatura, CLI, SDK e API.';
