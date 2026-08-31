from uuid import UUID


def can_manage_tenant(conn, tenant_organization_id: UUID, user_id: UUID) -> bool:
    return bool(
        conn.execute(
            """
            select 1
            from tenant_memberships
            where tenant_organization_id = %s
              and user_id = %s
              and role = 'tenant_admin'
            """,
            (tenant_organization_id, user_id),
        ).fetchone()
    )


def list_teams(conn, tenant_organization_id: UUID):
    return conn.execute(
        """
        select t.id, t.tenant_organization_id, t.name, t.slug, t.status,
          count(distinct tm.user_id)::int as members_total,
          count(distinct wa.workspace_id)::int as workspaces_total
        from teams t
        left join team_memberships tm on tm.team_id = t.id
        left join workspace_assignments wa on wa.team_id = t.id
        where t.tenant_organization_id = %s and t.status = 'active'
        group by t.id
        order by lower(t.name), t.id
        """,
        (tenant_organization_id,),
    ).fetchall()


def create_team(conn, tenant_organization_id: UUID, name: str, slug: str):
    return conn.execute(
        """
        insert into teams (tenant_organization_id, name, slug)
        values (%s, %s, %s)
        returning id, tenant_organization_id, name, slug, status,
          0::int as members_total, 0::int as workspaces_total
        """,
        (tenant_organization_id, name, slug),
    ).fetchone()


def unique_team_slug(conn, tenant_organization_id: UUID, base_slug: str) -> str:
    candidate = base_slug
    suffix = 2
    while conn.execute(
        "select 1 from teams where tenant_organization_id = %s and slug = %s",
        (tenant_organization_id, candidate),
    ).fetchone():
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate


def find_team(conn, team_id: UUID):
    return conn.execute(
        "select id, tenant_organization_id, name, slug, status from teams where id = %s and status = 'active'",
        (team_id,),
    ).fetchone()


def list_team_members(conn, team_id: UUID):
    return conn.execute(
        """
        select tm.team_id, tm.user_id, u.email, u.display_name, tm.role
        from team_memberships tm
        join users u on u.id = tm.user_id
        where tm.team_id = %s
        order by lower(u.display_name), u.id
        """,
        (team_id,),
    ).fetchall()


def upsert_team_member(conn, team_id: UUID, user_id: UUID, role: str) -> None:
    conn.execute(
        """
        insert into team_memberships (team_id, user_id, role)
        values (%s, %s, %s)
        on conflict (team_id, user_id) do update set role = excluded.role
        """,
        (team_id, user_id, role),
    )


def delete_team_member(conn, team_id: UUID, user_id: UUID) -> None:
    conn.execute("delete from team_memberships where team_id = %s and user_id = %s", (team_id, user_id))


def list_tenant_memberships(conn, tenant_organization_id: UUID):
    return conn.execute(
        """
        select tm.tenant_organization_id, tm.user_id, u.email, u.display_name, tm.role
        from tenant_memberships tm
        join users u on u.id = tm.user_id
        where tm.tenant_organization_id = %s
        order by lower(u.display_name), u.id
        """,
        (tenant_organization_id,),
    ).fetchall()


def list_organization_people(conn, organization_id: UUID):
    """Todo mundo que pertence a esta organizacao, com papel e equipes.

    Parte de `memberships` (que e o que o convite cria) e nao de
    `tenant_memberships`, que so tem quem recebeu papel de tenant explicito.
    Listar pelo segundo faria alguem recem-convidado sumir da tela — foi
    exatamente o que aconteceu.
    """
    return conn.execute(
        """
        select
          u.id as user_id,
          u.email,
          u.display_name,
          u.is_active,
          m.role,
          tm.role as tenant_role,
          coalesce(
            array_agg(t.name order by t.name) filter (where t.name is not null),
            '{}'
          ) as teams
        from memberships m
        join users u on u.id = m.user_id
        left join tenant_memberships tm
          on tm.user_id = u.id and tm.tenant_organization_id = m.organization_id
        left join team_memberships tmem on tmem.user_id = u.id
        left join teams t
          on t.id = tmem.team_id
         and t.tenant_organization_id = m.organization_id
         and t.status = 'active'
        where m.organization_id = %s
        group by u.id, u.email, u.display_name, u.is_active, m.role, tm.role
        order by lower(u.display_name), u.id
        """,
        (organization_id,),
    ).fetchall()


def upsert_tenant_membership(conn, tenant_organization_id: UUID, user_id: UUID, role: str) -> None:
    conn.execute(
        """
        insert into tenant_memberships (tenant_organization_id, user_id, role)
        values (%s, %s, %s)
        on conflict (tenant_organization_id, user_id) do update
          set role = excluded.role, updated_at = now()
        """,
        (tenant_organization_id, user_id, role),
    )


def list_workspace_assignments(conn, workspace_id: UUID):
    return conn.execute(
        """
        select wa.id, wa.workspace_id, wa.user_id, wa.team_id,
          coalesce(u.display_name, t.name) as assignee_name,
          u.email as assignee_email,
          wa.role
        from workspace_assignments wa
        left join users u on u.id = wa.user_id
        left join teams t on t.id = wa.team_id
        where wa.workspace_id = %s
        order by lower(coalesce(u.display_name, t.name)), wa.id
        """,
        (workspace_id,),
    ).fetchall()


def find_workspace(conn, workspace_id: UUID):
    return conn.execute(
        "select id, tenant_organization_id from workspaces where id = %s and status = 'active'",
        (workspace_id,),
    ).fetchone()


def upsert_workspace_assignment(
    conn,
    workspace_id: UUID,
    user_id: UUID | None,
    team_id: UUID | None,
    role: str,
    created_by: UUID,
) -> None:
    if user_id:
        conn.execute(
            """
            insert into workspace_assignments (workspace_id, user_id, role, created_by)
            values (%s, %s, %s, %s)
            on conflict (workspace_id, user_id) where user_id is not null
            do update set role = excluded.role, updated_at = now()
            """,
            (workspace_id, user_id, role, created_by),
        )
    else:
        conn.execute(
            """
            insert into workspace_assignments (workspace_id, team_id, role, created_by)
            values (%s, %s, %s, %s)
            on conflict (workspace_id, team_id) where team_id is not null
            do update set role = excluded.role, updated_at = now()
            """,
            (workspace_id, team_id, role, created_by),
        )


def delete_workspace_assignment(conn, workspace_id: UUID, assignment_id: UUID) -> None:
    conn.execute(
        "delete from workspace_assignments where workspace_id = %s and id = %s",
        (workspace_id, assignment_id),
    )
