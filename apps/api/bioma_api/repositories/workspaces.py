from uuid import UUID

from psycopg.types.json import Jsonb


def find_accessible_client(conn, context_id: UUID, is_admin: bool, user_id: UUID):
    """Resolve o contexto de um workspace ativo, com ou sem registro de cliente.

    Platform admin pode operar tanto o workspace interno quanto workspaces
    cliente. Demais usuários precisam de membership `client_user` direta em um
    workspace `client`; membership na organização interna nunca basta.

    **O workspace é a âncora, não o cliente** (mudança de 2026-08-07). Antes
    esta consulta partia de `clients`, o que tornava o registro comercial
    OBRIGATÓRIO para qualquer workspace existir na aplicação — e foi isso que
    obrigou a criar um cliente "EverGreen Internal", a agência fingindo ser
    cliente de si mesma só para o próprio workspace resolver.

    Agora parte de `workspaces` e o cliente entra por `left join`: quando
    existe, `id`/`name` continuam sendo os dele e nada muda para os 20+
    chamadores; quando não existe, `id` vem nulo e o workspace resolve mesmo
    assim. `organization_id` passa a vir do workspace, que é equivalente
    quando há cliente (a junção garantia isso) e correto quando não há.
    """
    return conn.execute(
        """
        select
          c.id,
          coalesce(c.name, w.name) as name,
          w.subject_organization_id as organization_id,
          o.name as organization_name,
          o.enabled_modules,
          w.id as workspace_id,
          w.tenant_organization_id,
          w.kind as workspace_kind,
          access.role as access_role
        from workspaces w
        join organizations o on o.id = w.subject_organization_id
        left join clients c on c.organization_id = w.subject_organization_id
        cross join lateral (
          select case
            when %s then 'platform_admin'
            else workspace_access_role(w.id, %s)
          end as role
        ) access
        where w.status = 'active'
          and (w.id = %s or c.id = %s)
          and access.role is not null
        order by case when w.id = %s then 0 else 1 end
        limit 1
        """,
        (is_admin, user_id, context_id, context_id, context_id),
    ).fetchone()


def find_accessible_organization(conn, organization_id: UUID, is_admin: bool, user_id: UUID):
    """Resolve uma organização operacional pelo mesmo gate de workspace."""
    return conn.execute(
        """
        select
          o.id as organization_id,
          o.enabled_modules,
          w.id as workspace_id,
          w.kind as workspace_kind,
          access.role as access_role
        from organizations o
        join workspaces w
          on w.subject_organization_id = o.id
         and w.status = 'active'
        cross join lateral (
          select case
            when %s then 'platform_admin'
            else workspace_access_role(w.id, %s)
          end as role
        ) access
        where o.id = %s
          and access.role is not null
        """,
        (is_admin, user_id, organization_id),
    ).fetchone()


def list_accessible_workspaces(conn, is_admin: bool, user_id: UUID):
    return conn.execute(
        """
        select
          w.id,
          w.tenant_organization_id,
          tenant.name as tenant_name,
          tenant.slug as tenant_slug,
          w.subject_organization_id as organization_id,
          subject.name as organization_name,
          subject.slug as organization_slug,
          w.kind,
          w.name,
          w.slug,
          w.status,
          case when w.kind = 'client' then c.id end as client_id,
          case when w.kind = 'agency_internal' then c.id end as legacy_client_id,
          c.id as operational_client_id,
          case when w.kind = 'client' then c.status end as client_status,
          case when w.kind = 'client' then c.responsible_name end as responsible_name,
          subject.enabled_modules,
          access.role as access_role,
          exists (
            select 1 from workspace_favorites favorite
            where favorite.workspace_id = w.id and favorite.user_id = %s
          ) as is_favorite,
          workspace_is_assigned(w.id, %s) as is_assigned
        from workspaces w
        join organizations tenant on tenant.id = w.tenant_organization_id
        join organizations subject on subject.id = w.subject_organization_id
        left join clients c on c.organization_id = w.subject_organization_id
        cross join lateral (
          select case
            when %s then 'platform_admin'
            else workspace_access_role(w.id, %s)
          end as role
        ) access
        where w.status = 'active'
          and access.role is not null
        order by
          case w.kind when 'agency_internal' then 0 else 1 end,
          lower(w.name),
          w.id
        """,
        (user_id, user_id, is_admin, user_id),
    ).fetchall()


def find_accessible_workspace(conn, workspace_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        """
        select w.id, w.tenant_organization_id,
          case when %s then 'platform_admin' else workspace_access_role(w.id, %s) end as access_role
        from workspaces w
        where w.id = %s
          and w.status = 'active'
          and (%s or workspace_access_role(w.id, %s) is not null)
        """,
        (is_admin, user_id, workspace_id, is_admin, user_id),
    ).fetchone()


def set_favorite(conn, workspace_id: UUID, user_id: UUID, favorite: bool) -> None:
    if favorite:
        conn.execute(
            """
            insert into workspace_favorites (user_id, workspace_id)
            values (%s, %s)
            on conflict do nothing
            """,
            (user_id, workspace_id),
        )
    else:
        conn.execute(
            "delete from workspace_favorites where user_id = %s and workspace_id = %s",
            (user_id, workspace_id),
        )


def list_saved_views(conn, user_id: UUID):
    return conn.execute(
        """
        select id, tenant_organization_id, name, filters
        from workspace_saved_views
        where user_id = %s
        order by lower(name), id
        """,
        (user_id,),
    ).fetchall()


def create_saved_view(conn, user_id: UUID, tenant_organization_id: UUID | None, name: str, filters: dict):
    return conn.execute(
        """
        insert into workspace_saved_views (user_id, tenant_organization_id, name, filters)
        values (%s, %s, %s, %s)
        returning id, tenant_organization_id, name, filters
        """,
        (user_id, tenant_organization_id, name, Jsonb(filters)),
    ).fetchone()


def delete_saved_view(conn, user_id: UUID, view_id: UUID) -> None:
    conn.execute(
        "delete from workspace_saved_views where id = %s and user_id = %s",
        (view_id, user_id),
    )


def find_platform_tenant_id(conn, user_id: UUID) -> UUID | None:
    row = conn.execute(
        """
        select o.id
        from memberships m
        join organizations o on o.id = m.organization_id
        where m.user_id = %s
          and m.role = 'eg_admin'
          and o.type = 'eg'
          and o.slug = 'eg'
        order by o.created_at asc
        limit 1
        """,
        (user_id,),
    ).fetchone()
    return row["id"] if row else None


def find_eg_tenant_id(conn) -> UUID | None:
    """Tenant EG, independente da associação do usuário chamador.

    Diferente de `find_platform_tenant_id` (que exige `eg_admin` do próprio
    usuário): usado por módulos onde `tenant_admin` também deve operar, e o
    gate de permissão real é feito separadamente (ex. `_require_tenant_manager`).
    """
    row = conn.execute(
        "select id from organizations where slug = 'eg' and type = 'eg' order by created_at asc limit 1",
    ).fetchone()
    return row["id"] if row else None


def provision_agency_workspace(conn, organization_id: UUID, workspace_name: str) -> UUID:
    row = conn.execute(
        """
        insert into workspaces (
          tenant_organization_id,
          subject_organization_id,
          kind,
          name,
          slug
        )
        select %s, %s, 'agency_internal', %s, o.slug
        from organizations o
        where o.id = %s and o.type in ('eg', 'agency')
        on conflict (subject_organization_id)
        do update set
          name = excluded.name,
          slug = excluded.slug,
          status = 'active',
          updated_at = now()
        where workspaces.kind = 'agency_internal'
          and workspaces.tenant_organization_id = excluded.tenant_organization_id
        returning id
        """,
        (organization_id, organization_id, workspace_name, organization_id),
    ).fetchone()
    if not row:
        raise RuntimeError("Não foi possível provisionar o workspace interno sem violar seus invariantes.")
    return row["id"]


def provision_client_workspace(
    conn,
    tenant_organization_id: UUID,
    organization_id: UUID,
    name: str,
    slug: str,
) -> UUID:
    row = conn.execute(
        """
        insert into workspaces (
          tenant_organization_id,
          subject_organization_id,
          kind,
          name,
          slug
        )
        values (%s, %s, 'client', %s, %s)
        on conflict (subject_organization_id)
        do update set
          name = excluded.name,
          slug = excluded.slug,
          status = 'active',
          updated_at = now()
        where workspaces.kind = 'client'
          and workspaces.tenant_organization_id = excluded.tenant_organization_id
        returning id
        """,
        (tenant_organization_id, organization_id, name, slug),
    ).fetchone()
    if not row:
        raise RuntimeError("Não foi possível provisionar o workspace cliente sem violar seus invariantes.")
    return row["id"]


def update_client_workspace_name(conn, organization_id: UUID, name: str) -> None:
    conn.execute(
        """
        update workspaces
        set name = %s, updated_at = now()
        where subject_organization_id = %s and kind = 'client'
        """,
        (name, organization_id),
    )
