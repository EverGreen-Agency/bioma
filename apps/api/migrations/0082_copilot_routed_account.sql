-- Liga a execução do copiloto à conta de assinatura que respondeu.
--
-- Sem isto, a trilha sabe QUE modelo respondeu mas não sabe DE QUE CONTA — e
-- sem a conta não dá pra mostrar a cota restante daquela assinatura, que é o
-- número que importa quando a cobrança é por assinatura, não por token
-- (decisão do Eduardo, 2026-08-04: "não seria ver nossa assinatura, quantidade
-- usada da cota... calcular com base no que pagamos de assinatura?").

alter table copilot_runs
  add column if not exists routed_account_id uuid references ai_provider_accounts(id) on delete set null;

create index if not exists idx_copilot_runs_routed_account on copilot_runs (routed_account_id) where routed_account_id is not null;
