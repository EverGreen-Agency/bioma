-- Convite para o time da EG (e para equipe), não só para cliente.
--
-- O que existia: `invites` com `role` travado em `client_user`, e o serviço
-- recusando explicitamente workspace interno (`require_kind="client"`). Ou
-- seja, convidar alguém da EG simplesmente não tinha caminho — a tela dizia
-- "Funcionalidade em breve" e estava sendo honesta. Para colocar uma pessoa no
-- time era preciso que ela JÁ tivesse conta, porque adicionar a equipe/tenant
-- exige um `user_id` existente.
--
-- Por que estender `invites` em vez de criar `tenant_invites`: o valor do
-- convite está no fluxo de aceite — token com hash, expiração, uso único,
-- criação de usuário e abertura de sessão, tudo já testado e com rota pública
-- funcionando. Uma tabela paralela duplicaria isso e as duas divergiriam na
-- primeira correção de segurança. O que muda de verdade é só O QUE o aceite
-- concede.
--
-- Três colunas novas, todas opcionais, para convite de cliente continuar
-- idêntico ao que era:
--
--   * `role` passa a aceitar `eg_admin` — quem entra pelo convite da EG vira
--     membro da organização EG, não de um cliente;
--   * `team_id` — a pessoa já cai na equipe certa. Sem isso, todo convite
--     exigiria um segundo passo manual, que é onde se perde;
--   * `tenant_role` — papel no tenant (`tenant_memberships`), separado do
--     papel de plataforma. Nulo mantém o comportamento antigo.

alter table invites drop constraint if exists invites_role_check;
alter table invites
  add constraint invites_role_check check (role in ('client_user', 'eg_admin'));

alter table invites
  add column if not exists team_id uuid references teams(id) on delete set null;

alter table invites
  add column if not exists tenant_role text
    check (tenant_role is null or tenant_role in ('tenant_admin', 'operator', 'approver', 'viewer'));

-- Convite de cliente nunca deve carregar equipe da EG: são mundos separados, e
-- misturá-los colocaria um usuário de cliente dentro de uma equipe interna. O
-- banco recusa em vez de confiar no código.
alter table invites drop constraint if exists invites_team_only_for_eg_check;
alter table invites
  add constraint invites_team_only_for_eg_check check (
    role = 'eg_admin' or (team_id is null and tenant_role is null)
  );

create index if not exists invites_team_idx on invites (team_id) where team_id is not null;
