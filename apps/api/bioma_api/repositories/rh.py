from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


def create_milestone_template(conn, tenant_organization_id: UUID, payload: dict[str, Any]):
    return conn.execute(
        """
        insert into onboarding_milestone_templates (tenant_organization_id, day_offset, title, description, status)
        values (%s, %s, %s, %s, %s)
        returning id, day_offset, title, description, status, created_at, updated_at
        """,
        (tenant_organization_id, payload["day_offset"], payload["title"], payload.get("description"), payload.get("status", "active")),
    ).fetchone()


def list_milestone_templates(conn, tenant_organization_id: UUID):
    return conn.execute(
        """
        select id, day_offset, title, description, status, created_at, updated_at
        from onboarding_milestone_templates
        where tenant_organization_id = %s
        order by status, day_offset
        """,
        (tenant_organization_id,),
    ).fetchall()


def active_milestone_templates(conn, tenant_organization_id: UUID):
    return conn.execute(
        """
        select id, day_offset, title
        from onboarding_milestone_templates
        where tenant_organization_id = %s and status = 'active'
        order by day_offset
        """,
        (tenant_organization_id,),
    ).fetchall()


def update_milestone_template(conn, tenant_organization_id: UUID, template_id: UUID, updates: dict[str, Any]):
    if not updates:
        return None
    columns = [f"{key} = %s" for key in updates]
    params = list(updates.values()) + [template_id, tenant_organization_id]
    return conn.execute(
        f"""
        update onboarding_milestone_templates
        set {", ".join(columns)}, updated_at = now()
        where id = %s and tenant_organization_id = %s
        returning id, day_offset, title, description, status, created_at, updated_at
        """,
        params,
    ).fetchone()


def create_onboarding_plan(conn, tenant_organization_id: UUID, user_id: UUID, hire_date, milestones: list[dict], created_by: UUID):
    return conn.execute(
        """
        insert into employee_onboarding_plans (tenant_organization_id, user_id, hire_date, milestones, created_by)
        values (%s, %s, %s, %s, %s)
        returning id
        """,
        (tenant_organization_id, user_id, hire_date, Jsonb(milestones), created_by),
    ).fetchone()["id"]


def find_existing_plan(conn, tenant_organization_id: UUID, user_id: UUID):
    return conn.execute(
        "select id from employee_onboarding_plans where tenant_organization_id = %s and user_id = %s",
        (tenant_organization_id, user_id),
    ).fetchone()


def get_onboarding_plan(conn, tenant_organization_id: UUID, plan_id: UUID):
    return conn.execute(
        """
        select p.id, p.user_id, u.email as user_email, u.display_name as user_name,
               p.hire_date, p.milestones, p.created_at, p.updated_at
        from employee_onboarding_plans p
        join users u on u.id = p.user_id
        where p.id = %s and p.tenant_organization_id = %s
        """,
        (plan_id, tenant_organization_id),
    ).fetchone()


def list_onboarding_plans(conn, tenant_organization_id: UUID):
    return conn.execute(
        """
        select p.id, p.user_id, u.email as user_email, u.display_name as user_name,
               p.hire_date, p.milestones, p.created_at, p.updated_at
        from employee_onboarding_plans p
        join users u on u.id = p.user_id
        where p.tenant_organization_id = %s
        order by p.hire_date desc
        """,
        (tenant_organization_id,),
    ).fetchall()


def update_milestone_status(conn, tenant_organization_id: UUID, plan_id: UUID, day_offset: int, status: str):
    return conn.execute(
        """
        update employee_onboarding_plans
        set milestones = (
          select jsonb_agg(
            case when (elem->>'day_offset')::int = %s
              then elem || jsonb_build_object(
                'status', %s::text,
                'completed_at', case when %s = 'done' then to_jsonb(now()) else 'null'::jsonb end
              )
              else elem
            end
          )
          from jsonb_array_elements(milestones) as elem
        ),
        updated_at = now()
        where id = %s and tenant_organization_id = %s
        returning id
        """,
        (day_offset, status, status, plan_id, tenant_organization_id),
    ).fetchone()


def create_satisfaction_score(conn, workspace_id: UUID, payload: dict[str, Any], created_by: UUID):
    return conn.execute(
        """
        insert into workspace_satisfaction_scores (workspace_id, score, source, notes, created_by)
        values (%s, %s, %s, %s, %s)
        returning id, workspace_id, score, source, notes, captured_at
        """,
        (workspace_id, payload["score"], payload.get("source", "manual"), payload.get("notes"), created_by),
    ).fetchone()


def list_satisfaction_scores(conn, workspace_id: UUID):
    return conn.execute(
        """
        select id, workspace_id, score, source, notes, captured_at
        from workspace_satisfaction_scores
        where workspace_id = %s
        order by captured_at desc
        """,
        (workspace_id,),
    ).fetchall()


def list_managed_workspaces(conn, user_id: UUID):
    return conn.execute(
        """
        select
          w.id as workspace_id,
          w.name as workspace_name,
          c.name as client_name,
          count(distinct proj.id)::int as projects_total,
          count(distinct d.id)::int as deliverables_total,
          count(distinct d.id) filter (where d.status = 'done')::int as deliverables_done,
          count(distinct d.id) filter (where d.due_at < now() and d.status <> 'done')::int as deliverables_overdue,
          count(distinct d.id) filter (where d.status = 'blocked')::int as deliverables_blocked
        from workspace_assignments wa
        join workspaces w on w.id = wa.workspace_id and w.status = 'active'
        join clients c on c.organization_id = w.subject_organization_id
        left join projects proj on proj.workspace_id = w.id
        left join deliverables d on d.project_id = proj.id
        where wa.user_id = %s and wa.role = 'workspace_manager'
        group by w.id, w.name, c.name
        order by w.name
        """,
        (user_id,),
    ).fetchall()


def latest_satisfaction_by_workspace(conn, workspace_ids: list[UUID]) -> dict[UUID, dict]:
    if not workspace_ids:
        return {}
    rows = conn.execute(
        """
        select distinct on (workspace_id) workspace_id, score, captured_at
        from workspace_satisfaction_scores
        where workspace_id = any(%s)
        order by workspace_id, captured_at desc
        """,
        (workspace_ids,),
    ).fetchall()
    return {row["workspace_id"]: row for row in rows}
