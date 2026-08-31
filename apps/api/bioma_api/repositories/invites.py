from datetime import datetime
from uuid import UUID


def create_invite(
    conn,
    organization_id: UUID,
    email: str | None,
    token_hash: str,
    expires_at: datetime,
    created_by: UUID,
    role: str = "client_user",
    team_id: UUID | None = None,
    tenant_role: str | None = None,
) -> UUID:
    """`role`/`team_id`/`tenant_role` (0088) distinguem convite de cliente de
    convite para o time da EG. Os defaults preservam o convite de cliente."""
    return conn.execute(
        """
        insert into invites (organization_id, email, token_hash, expires_at, created_by,
                             role, team_id, tenant_role)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (organization_id, email, token_hash, expires_at, created_by, role, team_id, tenant_role),
    ).fetchone()["id"]


def list_invites(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, email, expires_at, used_at, created_at, role, team_id, tenant_role
        from invites
        where organization_id = %s
        order by created_at desc
        limit 50
        """,
        (organization_id,),
    ).fetchall()


def delete_invite(conn, organization_id: UUID, invite_id: UUID) -> bool:
    deleted = conn.execute(
        "delete from invites where id = %s and organization_id = %s and used_at is null returning id",
        (invite_id, organization_id),
    ).fetchone()
    return deleted is not None


def find_valid_invite(conn, token_hash: str):
    return conn.execute(
        """
        select
          i.id,
          i.organization_id,
          i.email,
          i.expires_at,
          i.role,
          i.team_id,
          i.tenant_role,
          t.name as team_name,
          o.name as organization_name,
          coalesce(c.name, o.name) as client_name
        from invites i
        join organizations o on o.id = i.organization_id
        -- LEFT JOIN nos dois: convite da EG não tem registro de cliente e cai
        -- num workspace `agency_internal`. Antes as junções eram obrigatórias
        -- e travadas em `kind = 'client'`, o que fazia um convite de time
        -- válido parecer expirado — falha silenciosa e impossível de depurar
        -- pela mensagem.
        left join clients c on c.organization_id = i.organization_id
        left join teams t on t.id = i.team_id
        where exists (
          select 1 from workspaces w
          where w.subject_organization_id = i.organization_id
            and w.status = 'active'
            and (w.kind = 'client' or i.role in ('eg_admin', 'eg_member'))
        )
          and i.token_hash = %s
          and i.used_at is null
          and i.expires_at > now()
        """,
        (token_hash,),
    ).fetchone()


def mark_invite_used(conn, invite_id: UUID, user_id: UUID) -> None:
    conn.execute(
        "update invites set used_at = now(), used_by = %s where id = %s",
        (user_id, invite_id),
    )


def find_user_by_email(conn, email: str):
    return conn.execute(
        "select id from users where lower(email) = %s",
        (email.lower(),),
    ).fetchone()


def create_user(conn, email: str, display_name: str, password_hash: str) -> UUID:
    return conn.execute(
        """
        insert into users (email, display_name, password_hash)
        values (%s, %s, %s)
        returning id
        """,
        (email.lower(), display_name, password_hash),
    ).fetchone()["id"]


def create_membership(conn, user_id: UUID, organization_id: UUID, role: str) -> None:
    conn.execute(
        """
        insert into memberships (user_id, organization_id, role)
        values (%s, %s, %s)
        on conflict (user_id, organization_id) do nothing
        """,
        (user_id, organization_id, role),
    )


def add_to_team(conn, team_id: UUID, user_id: UUID) -> None:
    """Coloca a pessoa na equipe já no aceite.

    Sem isto o convite entregaria alguém sem equipe, e o segundo passo manual é
    justamente onde se esquece — a pessoa entra, não vê nada e vira chamado."""
    conn.execute(
        """
        insert into team_memberships (team_id, user_id, role)
        values (%s, %s, 'member')
        on conflict (team_id, user_id) do nothing
        """,
        (team_id, user_id),
    )


def add_tenant_membership(conn, tenant_organization_id: UUID, user_id: UUID, role: str) -> None:
    conn.execute(
        """
        insert into tenant_memberships (tenant_organization_id, user_id, role)
        values (%s, %s, %s)
        on conflict (tenant_organization_id, user_id) do update set role = excluded.role
        """,
        (tenant_organization_id, user_id, role),
    )


def create_session(conn, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
    conn.execute(
        "insert into sessions (user_id, token_hash, expires_at) values (%s, %s, %s)",
        (user_id, token_hash, expires_at),
    )
