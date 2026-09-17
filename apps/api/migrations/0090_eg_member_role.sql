-- Papel de EG que NÃO é administrador.
--
-- `memberships.role` só aceitava `eg_admin` e `client_user`. Consequência
-- prática, encontrada usando o produto: **todo convite ao time criava um
-- administrador**, porque não havia outra coisa para criar. Convidar um
-- estagiário dava a ele o mesmo poder de quem assina a empresa.
--
-- `eg_member` fecha esse buraco. A distinção que ele introduz, e que o código
-- passa a respeitar em dois predicados separados:
--
--   * **pertencer à EG** (`is_platform_member`) — decide o que a pessoa
--     ENXERGA: as telas internas existem para ela, e o acesso a workspace vem
--     das atribuições dela, como para qualquer um;
--   * **administrar a EG** (`is_platform_admin`) — decide o que ela MUDA:
--     convidar, conceder acesso, mexer em integração, feature flag, cofre.
--
-- Antes os dois eram a mesma pergunta, e é por isso que só existia um papel.
--
-- Ninguém muda de papel com esta migração: quem é `eg_admin` continua sendo.
-- Ela só passa a permitir a alternativa.

alter table memberships drop constraint if exists memberships_role_check;
alter table memberships
  add constraint memberships_role_check
  check (role in ('eg_admin', 'eg_member', 'client_user'));

-- O convite tambem precisa poder oferecer a alternativa (0088 fixou
-- `eg_admin`). A regra de que equipe/tenant_role so valem para convite interno
-- continua valendo, agora para os dois papeis da EG.
alter table invites drop constraint if exists invites_role_check;
alter table invites
  add constraint invites_role_check check (role in ('client_user', 'eg_admin', 'eg_member'));

alter table invites drop constraint if exists invites_team_only_for_eg_check;
alter table invites
  add constraint invites_team_only_for_eg_check check (
    role in ('eg_admin', 'eg_member') or (team_id is null and tenant_role is null)
  );
