import re
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


def list_clients(conn, is_admin: bool, user_id: UUID):
    return conn.execute(
        _client_summary_sql(_client_access_filter()),
        (is_admin, user_id),
    ).fetchall()


def create_organization(conn, name: str, slug: str, tenant_organization_id: UUID) -> UUID:
    return conn.execute(
        """
        insert into organizations (name, slug, type, parent_organization_id)
        values (%s, %s, 'client', %s)
        returning id
        """,
        (name, slug, tenant_organization_id),
    ).fetchone()["id"]


def create_client(
    conn,
    organization_id: UUID,
    name: str,
    status: str,
    responsible_name: str | None,
) -> UUID:
    return conn.execute(
        """
        insert into clients (organization_id, name, status, responsible_name)
        values (%s, %s, %s, %s)
        returning id
        """,
        (organization_id, name, status, responsible_name),
    ).fetchone()["id"]


def get_client_summary(conn, client_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        _client_summary_sql(f"and c.id = %s {_client_access_filter()}"),
        (client_id, is_admin, user_id),
    ).fetchone()


def list_artifacts(conn, organization_id: UUID, is_admin: bool):
    return conn.execute(
        """
        select id, title, kind, visibility, url, content, created_at
        from artifacts
        where organization_id = %s
          and (%s or visibility = 'client')
        order by created_at desc
        limit 50
        """,
        (organization_id, is_admin),
    ).fetchall()


def list_deliverables(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, title, status, due_at, assignee_emails, updated_at
        from deliverables
        where organization_id = %s
        order by
          case status
            when 'blocked' then 0
            when 'waiting_approval' then 1
            when 'in_progress' then 2
            when 'planned' then 3
            else 4
          end,
          due_at nulls last,
          updated_at desc
        limit 50
        """,
        (organization_id,),
    ).fetchall()


def list_approvals(conn, organization_id: UUID):
    return conn.execute(
        """
        select
          a.id,
          a.deliverable_id,
          d.title as deliverable_title,
          a.status,
          a.comment,
          a.created_at,
          a.decided_at
        from approvals a
        left join deliverables d on d.id = a.deliverable_id
        where a.organization_id = %s
        order by
          case a.status when 'pending' then 0 else 1 end,
          a.created_at desc
        limit 50
        """,
        (organization_id,),
    ).fetchall()


def list_sync_runs(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, source, status, summary, started_at, finished_at
        from sync_runs
        where organization_id = %s
        order by started_at desc
        limit 20
        """,
        (organization_id,),
    ).fetchall()


def list_audit_logs(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, actor_user_id, event_type, metadata, created_at
        from audit_logs
        where organization_id = %s
        order by created_at desc
        limit 20
        """,
        (organization_id,),
    ).fetchall()


def list_client_requests(conn, workspace_id: UUID):
    return conn.execute(
        """
        select r.id, r.category, r.title, r.detail, r.status, r.priority,
          r.requested_by, u.display_name as requested_by_name, r.assigned_to,
          r.resolution_summary, r.created_at, r.updated_at
        from client_requests r
        left join users u on u.id = r.requested_by
        where r.workspace_id = %s
        order by
          case r.status
            when 'waiting_client' then 0
            when 'submitted' then 1
            when 'triaged' then 2
            when 'in_progress' then 3
            else 4
          end,
          r.updated_at desc
        limit 100
        """,
        (workspace_id,),
    ).fetchall()


def create_client_request(conn, workspace_id: UUID, payload: dict[str, Any], user_id: UUID):
    return conn.execute(
        """
        insert into client_requests (
          workspace_id, category, title, detail, priority, requested_by
        ) values (%s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            workspace_id,
            payload["category"],
            payload["title"],
            payload.get("detail"),
            payload["priority"],
            user_id,
        ),
    ).fetchone()


def update_client_request(conn, workspace_id: UUID, request_id: UUID, updates: dict[str, Any]) -> bool:
    if not updates:
        return True
    set_clause = ", ".join(f"{column} = %s" for column in updates)
    result = conn.execute(
        f"update client_requests set {set_clause}, updated_at = now() where id = %s and workspace_id = %s",
        [*updates.values(), request_id, workspace_id],
    )
    return result.rowcount > 0


def update_client(conn, client_id: UUID, updates: dict[str, Any]) -> None:
    if not updates:
        return

    set_clause = ", ".join([f"{column} = %s" for column in updates])
    params = list(updates.values()) + [client_id]
    conn.execute(
        f"update clients set {set_clause}, updated_at = now() where id = %s",
        params,
    )


def find_client_for_lifecycle(conn, client_id: UUID):
    return conn.execute(
        """
        select c.id, c.name, c.status, c.organization_id,
          w.id as workspace_id, w.tenant_organization_id, w.status as workspace_status
        from clients c
        join workspaces w on w.subject_organization_id = c.organization_id and w.kind = 'client'
        where c.id = %s
        for update of c, w
        """,
        (client_id,),
    ).fetchone()


def archive_client(conn, client_id: UUID, workspace_id: UUID) -> None:
    conn.execute(
        "update clients set status = 'archived', updated_at = now() where id = %s",
        (client_id,),
    )
    conn.execute(
        "update workspaces set status = 'archived', updated_at = now() where id = %s",
        (workspace_id,),
    )


def list_client_storage_keys(conn, organization_id: UUID) -> list[str]:
    return [
        row["storage_key"]
        for row in conn.execute(
            "select storage_key from client_files where organization_id = %s order by id",
            (organization_id,),
        ).fetchall()
    ]


def purge_client_organization(conn, organization_id: UUID) -> None:
    conn.execute("delete from organizations where id = %s", (organization_id,))


def update_organization_name(conn, organization_id: UUID, name: str) -> None:
    conn.execute(
        "update organizations set name = %s, updated_at = now() where id = %s",
        (name, organization_id),
    )


def update_organization_modules(conn, organization_id: UUID, modules: list[str]) -> None:
    conn.execute(
        "update organizations set enabled_modules = %s, updated_at = now() where id = %s",
        (Jsonb(modules), organization_id),
    )


def create_artifact(
    conn,
    organization_id: UUID,
    title: str,
    kind: str,
    visibility: str,
    content: str | None,
    url: str | None,
    created_by: UUID,
) -> UUID:
    return conn.execute(
        """
        insert into artifacts (organization_id, title, kind, visibility, content, url, created_by)
        values (%s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (organization_id, title, kind, visibility, content, url, created_by),
    ).fetchone()["id"]


def update_artifact(conn, organization_id: UUID, artifact_id: UUID, updates: dict[str, Any]) -> bool:
    if not updates:
        return True

    set_clause = ", ".join([f"{column} = %s" for column in updates])
    params = list(updates.values()) + [artifact_id, organization_id]
    updated = conn.execute(
        f"update artifacts set {set_clause} where id = %s and organization_id = %s returning id",
        params,
    ).fetchone()
    return updated is not None


def delete_artifact(conn, organization_id: UUID, artifact_id: UUID) -> bool:
    deleted = conn.execute(
        "delete from artifacts where id = %s and organization_id = %s returning id",
        (artifact_id, organization_id),
    ).fetchone()
    return deleted is not None


def create_deliverable(
    conn,
    organization_id: UUID,
    title: str,
    status: str,
    due_at,
) -> UUID:
    return conn.execute(
        """
        insert into deliverables (organization_id, title, status, due_at)
        values (%s, %s, %s, %s)
        returning id
        """,
        (organization_id, title, status, due_at),
    ).fetchone()["id"]


def update_deliverable(conn, organization_id: UUID, deliverable_id: UUID, updates: dict[str, Any]) -> bool:
    if not updates:
        return True

    set_clause = ", ".join([f"{column} = %s" for column in updates])
    params = list(updates.values()) + [deliverable_id, organization_id]
    updated = conn.execute(
        f"""
        update deliverables
        set {set_clause}, updated_at = now()
        where id = %s and organization_id = %s
        returning id
        """,
        params,
    ).fetchone()
    return updated is not None


def delete_deliverable(conn, organization_id: UUID, deliverable_id: UUID) -> bool:
    conn.execute(
        "delete from approvals where deliverable_id = %s and organization_id = %s",
        (deliverable_id, organization_id),
    )
    deleted = conn.execute(
        "delete from deliverables where id = %s and organization_id = %s returning id",
        (deliverable_id, organization_id),
    ).fetchone()
    return deleted is not None


def get_deliverable(conn, organization_id: UUID, deliverable_id: UUID):
    return conn.execute(
        "select id, status from deliverables where id = %s and organization_id = %s",
        (deliverable_id, organization_id),
    ).fetchone()


def get_pending_approval(conn, organization_id: UUID, deliverable_id: UUID):
    return conn.execute(
        """
        select id
        from approvals
        where organization_id = %s and deliverable_id = %s and status = 'pending'
        """,
        (organization_id, deliverable_id),
    ).fetchone()


def create_approval(
    conn,
    organization_id: UUID,
    deliverable_id: UUID,
    requested_by: UUID,
    comment: str | None,
) -> UUID:
    return conn.execute(
        """
        insert into approvals (organization_id, deliverable_id, requested_by, status, comment)
        values (%s, %s, %s, 'pending', %s)
        returning id
        """,
        (organization_id, deliverable_id, requested_by, comment),
    ).fetchone()["id"]


def get_approval(conn, organization_id: UUID, approval_id: UUID):
    return conn.execute(
        """
        select id, deliverable_id, status
        from approvals
        where id = %s and organization_id = %s
        """,
        (approval_id, organization_id),
    ).fetchone()


def decide_approval(conn, approval_id: UUID, status: str, comment: str | None, decided_by: UUID) -> None:
    conn.execute(
        """
        update approvals
        set status = %s, comment = coalesce(%s, comment), decided_by = %s, decided_at = now()
        where id = %s
        """,
        (status, comment, decided_by, approval_id),
    )


def update_waiting_deliverable_status(conn, deliverable_id: UUID, status: str) -> None:
    conn.execute(
        """
        update deliverables
        set status = %s, updated_at = now()
        where id = %s and status = 'waiting_approval'
        """,
        (status, deliverable_id),
    )


def write_audit(conn, actor_user_id: UUID, organization_id: UUID, event_type: str, metadata: dict[str, Any]) -> None:
    conn.execute(
        """
        insert into audit_logs (actor_user_id, organization_id, event_type, metadata)
        values (%s, %s, %s, %s)
        """,
        (actor_user_id, organization_id, event_type, Jsonb(metadata)),
    )


def list_leads(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, name, company, role_title, email, phone, linkedin_url, source, stage,
               expected_value, notes, created_at, updated_at
        from leads
        where organization_id = %s
        order by
          case stage
            when 'new' then 0
            when 'qualifying' then 1
            when 'meeting' then 2
            when 'proposal' then 3
            when 'won' then 4
            else 5
          end,
          updated_at desc
        """,
        (organization_id,),
    ).fetchall()


def create_lead(conn, organization_id: UUID, payload: dict[str, Any]) -> UUID:
    return conn.execute(
        """
        insert into leads (
          organization_id, name, company, role_title, email, phone, linkedin_url,
          source, stage, expected_value, notes
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            organization_id,
            payload["name"],
            payload.get("company"),
            payload.get("role_title"),
            payload.get("email"),
            payload.get("phone"),
            payload.get("linkedin_url"),
            payload.get("source"),
            payload.get("stage", "new"),
            payload.get("expected_value"),
            payload.get("notes"),
        ),
    ).fetchone()["id"]


def update_lead(conn, organization_id: UUID, lead_id: UUID, updates: dict[str, Any]) -> bool:
    return _update_scoped_row(conn, "leads", organization_id, lead_id, updates)


def delete_lead(conn, organization_id: UUID, lead_id: UUID) -> bool:
    return _delete_scoped_row(conn, "leads", organization_id, lead_id)


def list_financial_records(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, kind, title, amount, currency, status, contract_start_at, contract_end_at,
               due_at, paid_at, notes, created_at, updated_at
        from financial_records
        where organization_id = %s
        order by due_at nulls last, updated_at desc
        """,
        (organization_id,),
    ).fetchall()


def create_financial_record(conn, organization_id: UUID, payload: dict[str, Any]) -> UUID:
    return conn.execute(
        """
        insert into financial_records (
          organization_id, kind, title, amount, currency, status, contract_start_at,
          contract_end_at, due_at, paid_at, notes
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            organization_id,
            payload["kind"],
            payload["title"],
            payload.get("amount"),
            payload.get("currency", "BRL"),
            payload.get("status", "open"),
            payload.get("contract_start_at"),
            payload.get("contract_end_at"),
            payload.get("due_at"),
            payload.get("paid_at"),
            payload.get("notes"),
        ),
    ).fetchone()["id"]


def update_financial_record(conn, organization_id: UUID, record_id: UUID, updates: dict[str, Any]) -> bool:
    return _update_scoped_row(conn, "financial_records", organization_id, record_id, updates)


def delete_financial_record(conn, organization_id: UUID, record_id: UUID) -> bool:
    return _delete_scoped_row(conn, "financial_records", organization_id, record_id)


def get_portfolio_summary(conn) -> dict[str, Any]:
    """Agregado real da carteira de clientes, usado no Cockpit do time EG.

    Escopo: apenas organizações de CLIENTE. A EverGreen tem uma linha própria
    em `clients` (o workspace interno), então filtrar só por
    `organization_id in (select organization_id from clients)` **incluía** a
    própria EG nos números — por isso todas as consultas aqui excluem
    explicitamente `organizations.slug = 'eg'`.
    """
    revenue = conn.execute(
        """
        with client_orgs as (
          select c.organization_id
          from clients c
          join organizations o on o.id = c.organization_id
          where o.slug <> 'eg'
        )
        select coalesce(sum(amount), 0) as total
        from financial_records
        where kind = 'invoice' and status = 'paid'
          and paid_at >= date_trunc('month', now())
          and paid_at < date_trunc('month', now()) + interval '1 month'
          and organization_id in (select organization_id from client_orgs)
        """
    ).fetchone()

    mrr = conn.execute(
        """
        with client_orgs as (
          select c.organization_id
          from clients c
          join organizations o on o.id = c.organization_id
          where o.slug <> 'eg'
        )
        select coalesce(sum(amount), 0) as total
        from financial_records
        where kind = 'contract' and status in ('open', 'paid')
          and (contract_end_at is null or contract_end_at >= current_date)
          and organization_id in (select organization_id from client_orgs)
        """
    ).fetchone()

    overdue_deliverables = conn.execute(
        """
        with client_orgs as (
          select c.organization_id
          from clients c
          join organizations o on o.id = c.organization_id
          where o.slug <> 'eg'
        )
        select count(*) as total
        from deliverables
        where due_at is not null and due_at < now() and status <> 'done'
          and organization_id in (select organization_id from client_orgs)
        """
    ).fetchone()

    clients_at_risk = conn.execute(
        """
        with client_orgs as (
          select c.organization_id
          from clients c
          join organizations o on o.id = c.organization_id
          where o.slug <> 'eg'
        )
        select count(distinct organization_id) as total
        from (
          select organization_id from deliverables
          where due_at is not null and due_at < now() and status <> 'done'
          union
          select organization_id from financial_records
          where status = 'overdue'
        ) at_risk
        where organization_id in (select organization_id from client_orgs)
        """
    ).fetchone()

    # Contagem por status: o Cockpit dizia "N clientes ativos" contando todos
    # os clientes externos, inclusive onboarding/pausado/arquivado.
    client_counts = conn.execute(
        """
        select
          count(*) filter (where c.status = 'active')::int as active,
          count(*)::int as total
        from clients c
        join organizations o on o.id = c.organization_id
        where o.slug <> 'eg'
        """
    ).fetchone()

    # Listas acionáveis: sem elas o Cockpit só mostra um número e obriga a
    # entrar cliente por cliente pra descobrir o que fazer.
    overdue_items = conn.execute(
        """
        select d.id, d.title, d.status, d.due_at, c.id as client_id, c.name as client_name
        from deliverables d
        join clients c on c.organization_id = d.organization_id
        join organizations o on o.id = c.organization_id
        where d.due_at is not null and d.due_at < now() and d.status <> 'done'
          and o.slug <> 'eg'
        order by d.due_at asc
        limit 8
        """
    ).fetchall()

    pending_approvals = conn.execute(
        """
        select a.id, d.title as deliverable_title, a.created_at,
               c.id as client_id, c.name as client_name
        from approvals a
        left join deliverables d on d.id = a.deliverable_id
        join clients c on c.organization_id = a.organization_id
        join organizations o on o.id = c.organization_id
        where a.status = 'pending' and o.slug <> 'eg'
        order by a.created_at asc
        limit 8
        """
    ).fetchall()

    # Conexao ativa que parou de sincronizar: a causa mais silenciosa de numero
    # errado no painel. Sem isso, "zero investimento" e "sync parado" sao
    # visualmente identicos. `last_synced_at is null` = nunca sincronizou.
    stale_connections = conn.execute(
        """
        select pc.provider, pc.display_name, pc.last_synced_at, pc.last_error_message,
               c.id as client_id, c.name as client_name,
               case
                 when pc.last_synced_at is null then null
                 else extract(day from now() - pc.last_synced_at)::int
               end as days_stale
        from performance_connections pc
        join clients c on c.id = pc.client_id
        join organizations o on o.id = c.organization_id
        where o.slug <> 'eg'
          and pc.status = 'active'
          and (pc.last_synced_at is null or pc.last_synced_at < now() - interval '3 days')
        order by pc.last_synced_at asc nulls first
        limit 10
        """
    ).fetchall()

    radar_awaiting = conn.execute(
        """
        select count(*) as total
        from local_radar_prospects
        where review_status = 'audited'
        """
    ).fetchone()

    return {
        "monthly_revenue_cents": round((revenue["total"] or 0) * 100),
        "mrr_cents": round((mrr["total"] or 0) * 100),
        "overdue_deliverables": overdue_deliverables["total"],
        "clients_at_risk": clients_at_risk["total"],
        "clients_active": client_counts["active"],
        "clients_total": client_counts["total"],
        "overdue_items": [dict(row) for row in overdue_items],
        "pending_approvals": [dict(row) for row in pending_approvals],
        "stale_connections": [dict(row) for row in stale_connections],
        "radar_prospects_awaiting": radar_awaiting["total"],
    }


def list_performance_metrics(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, period_start, period_end, channel, metric, value, source, notes, captured_at
        from performance_metrics
        where organization_id = %s
        order by period_start desc, channel asc, metric asc
        """,
        (organization_id,),
    ).fetchall()


def create_performance_metric(conn, organization_id: UUID, payload: dict[str, Any]) -> UUID:
    return conn.execute(
        """
        insert into performance_metrics (
          organization_id, period_start, period_end, channel, metric, value, source, notes
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            organization_id,
            payload["period_start"],
            payload["period_end"],
            payload["channel"],
            payload["metric"],
            payload["value"],
            payload.get("source", "manual"),
            payload.get("notes"),
        ),
    ).fetchone()["id"]


def update_performance_metric(conn, organization_id: UUID, metric_id: UUID, updates: dict[str, Any]) -> bool:
    return _update_scoped_row(conn, "performance_metrics", organization_id, metric_id, updates, touch_updated_at=False)


def delete_performance_metric(conn, organization_id: UUID, metric_id: UUID) -> bool:
    return _delete_scoped_row(conn, "performance_metrics", organization_id, metric_id)


def unique_org_slug(conn, base_slug: str) -> str:
    slug = _slugify(base_slug)
    candidate = slug
    suffix = 2
    while conn.execute("select 1 from organizations where slug = %s", (candidate,)).fetchone():
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def _update_scoped_row(
    conn,
    table: str,
    organization_id: UUID,
    row_id: UUID,
    updates: dict[str, Any],
    touch_updated_at: bool = True,
) -> bool:
    if not updates:
        return True

    update_values = dict(updates)
    if touch_updated_at:
        update_values["updated_at"] = "now()"
        set_clause = ", ".join(
            [f"{column} = now()" if column == "updated_at" else f"{column} = %s" for column in update_values]
        )
        params = [value for column, value in update_values.items() if column != "updated_at"]
    else:
        set_clause = ", ".join([f"{column} = %s" for column in update_values])
        params = list(update_values.values())

    params.extend([row_id, organization_id])
    updated = conn.execute(
        f"update {table} set {set_clause} where id = %s and organization_id = %s returning id",
        params,
    ).fetchone()
    return updated is not None


def _delete_scoped_row(conn, table: str, organization_id: UUID, row_id: UUID) -> bool:
    deleted = conn.execute(
        f"delete from {table} where id = %s and organization_id = %s returning id",
        (row_id, organization_id),
    ).fetchone()
    return deleted is not None


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "cliente"


def _client_access_filter() -> str:
    return """
      and (
        %s
        or exists (
          select 1
          from workspaces w
          where w.subject_organization_id = c.organization_id
            and w.kind = 'client'
            and w.status = 'active'
            and workspace_access_role(w.id, %s) is not null
        )
      )
    """


def _client_summary_sql(extra_where: str = "") -> str:
    return f"""
        select
          c.id,
          c.organization_id,
          o.name as organization_name,
          o.slug as organization_slug,
          c.name,
          c.status,
          c.responsible_name,
          o.enabled_modules,
          count(distinct d.id)::int as deliverables_total,
          count(distinct a.id) filter (where a.status = 'pending')::int as approvals_pending,
          count(distinct ar.id) filter (where ar.visibility = 'client')::int as artifacts_client
        from clients c
        join organizations o on o.id = c.organization_id
        left join deliverables d on d.organization_id = c.organization_id
        left join approvals a on a.organization_id = c.organization_id
        left join artifacts ar on ar.organization_id = c.organization_id
        where 1 = 1
          {extra_where}
        group by c.id, o.id
        order by c.created_at desc
    """

def list_my_deliverables(conn, user_email: str, is_admin: bool, user_id: UUID):
    return conn.execute(
        """
        select
            d.id, d.title, d.status, d.due_at, d.assignee_emails, d.updated_at,
            c.id as client_id, c.name as client_name
        from deliverables d
        join organizations o on o.id = d.organization_id
        join clients c on c.organization_id = o.id
        where d.assignee_emails ? %s
          and (
            %s
            or exists (
              select 1
              from workspaces w
              where w.subject_organization_id = d.organization_id
                and w.kind = 'client'
                and w.status = 'active'
                and workspace_access_role(w.id, %s) is not null
            )
          )
        order by d.due_at nulls last, d.updated_at desc
        limit 50
        """,
        (user_email, is_admin, user_id),
    ).fetchall()


def get_portfolio_performance(conn, days: int = 30) -> list[dict[str, Any]]:
    """Performance de mídia da carteira inteira, um cliente por linha.

    É o rollup executivo que faltava: cada cliente já tem a aba Métricas
    unificada, mas comparar a carteira exigia entrar cliente por cliente.
    Lê as mesmas tabelas que os syncs reais populam — sem credencial
    configurada as linhas ficam zeradas, nunca inventadas.
    """
    return conn.execute(
        """
        with client_rows as (
          select c.id as client_id, c.name as client_name,
                 w.id as workspace_id, c.status
          from clients c
          join organizations o on o.id = c.organization_id
          join workspaces w on w.subject_organization_id = c.organization_id
           and w.kind = 'client' and w.status = 'active'
          where o.slug <> 'eg'
        ),
        google as (
          select client_id,
                 coalesce(sum(cost_micros), 0) / 10000 as spend_cents,
                 coalesce(sum(conversions), 0) as conversions
          from ads_campaign_daily
          where date >= current_date - %s::int
          group by client_id
        ),
        meta as (
          select workspace_id,
                 coalesce(sum(spend_cents), 0) as spend_cents,
                 coalesce(sum(leads), 0) as leads
          from workspace_meta_ads_daily_metrics
          where date >= current_date - %s::int
          group by workspace_id
        ),
        li as (
          select workspace_id,
                 coalesce(sum(spend_cents), 0) as spend_cents,
                 coalesce(sum(leads), 0) as leads
          from workspace_linkedin_ads_daily_metrics
          where date >= current_date - %s::int
          group by workspace_id
        ),
        targets as (
          select client_id, target_leads, budget_micros
          from monthly_targets
          where month = date_trunc('month', current_date)::date
        )
        select cr.client_id, cr.client_name, cr.workspace_id, cr.status,
               coalesce(g.spend_cents, 0)::bigint as google_spend_cents,
               coalesce(m.spend_cents, 0)::bigint as meta_spend_cents,
               coalesce(l.spend_cents, 0)::bigint as linkedin_spend_cents,
               (coalesce(g.spend_cents, 0) + coalesce(m.spend_cents, 0)
                + coalesce(l.spend_cents, 0))::bigint as total_spend_cents,
               (coalesce(g.conversions, 0) + coalesce(m.leads, 0)
                + coalesce(l.leads, 0))::bigint as total_leads,
               t.target_leads::float as target_leads,
               (t.budget_micros / 10000)::bigint as budget_cents
        from client_rows cr
        left join google g on g.client_id = cr.client_id
        left join meta m on m.workspace_id = cr.workspace_id
        left join li l on l.workspace_id = cr.workspace_id
        left join targets t on t.client_id = cr.client_id
        order by total_spend_cents desc, cr.client_name
        """,
        (days, days, days),
    ).fetchall()


def upsert_monthly_target(
    conn,
    client_id: UUID,
    target_leads: float | None,
    budget_cents: int | None,
) -> bool:
    """Meta do mês corrente do cliente. As colunas existiam desde a 0003 e nunca
    tinham tido escrita nem leitura pela API — agora fecham o ciclo meta ×
    realizado no rollup do Cockpit."""
    row = conn.execute(
        """
        insert into monthly_targets (client_id, organization_id, month, target_leads, budget_micros)
        select c.id, c.organization_id, date_trunc('month', current_date)::date, %s, %s
        from clients c where c.id = %s
        on conflict (client_id, month)
        do update set target_leads = excluded.target_leads,
                      budget_micros = excluded.budget_micros,
                      updated_at = now()
        returning client_id
        """,
        # 1 centavo = 10.000 micros (1 unidade monetaria = 1.000.000). O rollup
        # le com /10000, então a escrita precisa do mesmo fator.
        (target_leads, budget_cents * 10_000 if budget_cents is not None else None, client_id),
    ).fetchone()
    return row is not None
