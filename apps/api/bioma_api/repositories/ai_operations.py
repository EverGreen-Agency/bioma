from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


def list_subscriptions(conn, organization_id: UUID):
    return conn.execute(
        """
        select s.id, s.provider, s.product_name, s.billing_mode, s.billing_cycle,
          s.billing_cycle_months, s.amount_cents, s.currency, s.seats, s.status,
          s.renews_at, s.owner_label, s.notes, s.created_at, s.updated_at,
          q.id as quota_id, q.total_units, q.used_units, q.unit as quota_unit,
          q.source as quota_source, q.period_start, q.period_end,
          q.measured_at, q.notes as quota_notes
        from ai_provider_subscriptions s
        left join lateral (
          select *
          from ai_quota_snapshots snapshot
          where snapshot.subscription_id = s.id
          order by snapshot.measured_at desc
          limit 1
        ) q on true
        where s.organization_id = %s
        order by (s.status = 'active') desc, s.provider, s.product_name
        """,
        (organization_id,),
    ).fetchall()


def create_subscription(conn, organization_id: UUID, user_id: UUID, payload: dict[str, Any]):
    return conn.execute(
        """
        insert into ai_provider_subscriptions (
          organization_id, provider, product_name, billing_mode, billing_cycle,
          billing_cycle_months, amount_cents, currency, seats, status, renews_at,
          owner_label, notes, created_by, updated_by
        )
        values (%s, %s, %s, %s, %s, %s, %s, upper(%s), %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            organization_id,
            payload["provider"].strip(),
            payload["product_name"].strip(),
            payload["billing_mode"],
            payload["billing_cycle"],
            payload["billing_cycle_months"],
            payload["amount_cents"],
            payload["currency"],
            payload["seats"],
            payload["status"],
            payload.get("renews_at"),
            payload.get("owner_label"),
            payload.get("notes"),
            user_id,
            user_id,
        ),
    ).fetchone()


def update_subscription(
    conn,
    organization_id: UUID,
    subscription_id: UUID,
    user_id: UUID,
    updates: dict[str, Any],
) -> bool:
    allowed = {
        "provider",
        "product_name",
        "billing_mode",
        "billing_cycle",
        "billing_cycle_months",
        "amount_cents",
        "currency",
        "seats",
        "status",
        "renews_at",
        "owner_label",
        "notes",
    }
    updates = {key: value for key, value in updates.items() if key in allowed}
    if not updates:
        return True
    assignments = [f"{key} = %s" for key in updates]
    values = list(updates.values())
    assignments.extend(["updated_by = %s", "updated_at = now()"])
    values.extend([user_id, subscription_id, organization_id])
    row = conn.execute(
        f"""
        update ai_provider_subscriptions
        set {", ".join(assignments)}
        where id = %s and organization_id = %s
        returning id
        """,
        values,
    ).fetchone()
    return bool(row)


def create_quota_snapshot(
    conn,
    organization_id: UUID,
    subscription_id: UUID,
    user_id: UUID,
    payload: dict[str, Any],
):
    return conn.execute(
        """
        insert into ai_quota_snapshots (
          subscription_id, total_units, used_units, unit, source, period_start,
          period_end, notes, created_by
        )
        select s.id, %s, %s, %s, %s, %s, %s, %s, %s
        from ai_provider_subscriptions s
        where s.id = %s and s.organization_id = %s
        returning id
        """,
        (
            payload.get("total_units"),
            payload.get("used_units"),
            payload["unit"],
            payload["source"],
            payload.get("period_start"),
            payload.get("period_end"),
            payload.get("notes"),
            user_id,
            subscription_id,
            organization_id,
        ),
    ).fetchone()


def usage_current_month(conn, organization_id: UUID):
    return conn.execute(
        """
        select provider, model, source, currency, count(*)::int as events,
          coalesce(sum(input_units), 0)::bigint as input_units,
          coalesce(sum(output_units), 0)::bigint as output_units,
          coalesce(sum(cached_units), 0)::bigint as cached_units,
          coalesce(sum(cost_cents), 0)::bigint as known_cost_cents,
          count(*) filter (where cost_cents is null)::int as unknown_cost_events
        from ai_usage_events
        where organization_id = %s
          and occurred_at >= date_trunc('month', now())
        group by provider, model, source, currency
        order by known_cost_cents desc, provider, model
        """,
        (organization_id,),
    ).fetchall()


def create_usage_event(conn, organization_id: UUID, user_id: UUID | None, payload: dict[str, Any]):
    return conn.execute(
        """
        insert into ai_usage_events (
          organization_id, workspace_id, workflow_run_id, user_id, provider,
          model, source, external_event_id, input_units, output_units,
          cached_units, unit, cost_cents, currency, metadata, occurred_at
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          upper(%s), %s, coalesce(%s, now()))
        on conflict (organization_id, provider, external_event_id)
          where external_event_id is not null
        do update set metadata = ai_usage_events.metadata || excluded.metadata
        returning id
        """,
        (
            organization_id,
            payload.get("workspace_id"),
            payload.get("workflow_run_id"),
            user_id,
            payload["provider"],
            payload.get("model"),
            payload["source"],
            payload.get("external_event_id"),
            payload.get("input_units"),
            payload.get("output_units"),
            payload.get("cached_units"),
            payload.get("unit", "tokens"),
            payload.get("cost_cents"),
            payload.get("currency", "USD"),
            Jsonb(payload.get("metadata", {})),
            payload.get("occurred_at"),
        ),
    ).fetchone()


def list_definitions(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, slug, name, version, description, source_ref, status,
          input_schema, steps, created_at
        from ai_workflow_definitions
        where organization_id = %s
        order by slug, version desc
        """,
        (organization_id,),
    ).fetchall()


def install_definition(conn, organization_id: UUID, user_id: UUID, template: dict[str, Any]):
    return conn.execute(
        """
        insert into ai_workflow_definitions (
          organization_id, slug, name, version, description, source_ref,
          status, input_schema, steps, created_by
        )
        values (%s, %s, %s, %s, %s, %s, 'active', %s, %s, %s)
        on conflict (organization_id, slug, version)
        do update set
          name = excluded.name,
          description = excluded.description,
          source_ref = excluded.source_ref,
          input_schema = excluded.input_schema,
          steps = excluded.steps
        returning id
        """,
        (
            organization_id,
            template["slug"],
            template["name"],
            template["version"],
            template["description"],
            template["source_ref"],
            Jsonb(template["input_schema"]),
            Jsonb(template["steps"]),
            user_id,
        ),
    ).fetchone()


def get_definition(conn, organization_id: UUID, definition_id: UUID):
    return conn.execute(
        """
        select id, slug, name, version, description, source_ref, status,
          input_schema, steps, created_at
        from ai_workflow_definitions
        where id = %s and organization_id = %s
        """,
        (definition_id, organization_id),
    ).fetchone()


def workspace_exists(conn, workspace_id: UUID) -> bool:
    return bool(conn.execute("select 1 from workspaces where id = %s", (workspace_id,)).fetchone())


def create_run(
    conn,
    organization_id: UUID,
    user_id: UUID,
    definition: dict[str, Any],
    payload: dict[str, Any],
):
    first_step = definition["steps"][0]["key"] if definition["steps"] else None
    row = conn.execute(
        """
        insert into ai_workflow_runs (
          organization_id, workspace_id, definition_id, requested_by, status,
          idempotency_key, input, current_step_key, estimated_cost_cents, currency
        )
        values (%s, %s, %s, %s, 'pending_approval', %s, %s, %s, %s, upper(%s))
        on conflict (organization_id, idempotency_key)
        do update set idempotency_key = excluded.idempotency_key
        returning id
        """,
        (
            organization_id,
            payload.get("workspace_id"),
            definition["id"],
            user_id,
            payload["idempotency_key"],
            Jsonb(payload.get("input", {})),
            first_step,
            payload.get("estimated_cost_cents"),
            payload.get("currency", "BRL"),
        ),
    ).fetchone()
    existing_steps = conn.execute(
        "select 1 from ai_workflow_step_runs where run_id = %s limit 1",
        (row["id"],),
    ).fetchone()
    if not existing_steps:
        for position, step in enumerate(definition["steps"]):
            conn.execute(
                """
                insert into ai_workflow_step_runs (
                  run_id, step_key, position, name, description, interactive,
                  task_kind, capability, status
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                """,
                (
                    row["id"],
                    step["key"],
                    position,
                    step["name"],
                    step.get("description"),
                    step.get("interactive", False),
                    step.get("task_kind", "content_draft"),
                    step.get("capability", "content"),
                ),
            )
    return row


def approve_run(conn, organization_id: UUID, run_id: UUID, user_id: UUID):
    run = conn.execute(
        """
        select id, current_step_key
        from ai_workflow_runs
        where id = %s and organization_id = %s and status = 'pending_approval'
        for update
        """,
        (run_id, organization_id),
    ).fetchone()
    if not run:
        return None
    current_step = conn.execute(
        """
        select id, position, status
        from ai_workflow_step_runs
        where run_id = %s and step_key = %s
        for update
        """,
        (run_id, run["current_step_key"]),
    ).fetchone()
    if current_step and current_step["status"] == "waiting_approval":
        conn.execute(
            """
            update ai_workflow_step_runs
            set status = 'completed', finished_at = coalesce(finished_at, now()), updated_at = now()
            where id = %s
            """,
            (current_step["id"],),
        )
        next_step = conn.execute(
            """
            select step_key
            from ai_workflow_step_runs
            where run_id = %s and position > %s and status = 'pending'
            order by position
            limit 1
            """,
            (run_id, current_step["position"]),
        ).fetchone()
        if not next_step:
            return conn.execute(
                """
                update ai_workflow_runs
                set status = 'completed', current_step_key = null, approved_by = %s,
                  approved_at = now(), finished_at = now(), updated_at = now()
                where id = %s
                returning id
                """,
                (user_id, run_id),
            ).fetchone()
        return conn.execute(
            """
            update ai_workflow_runs
            set status = 'ready', current_step_key = %s, approved_by = %s,
              approved_at = now(), updated_at = now()
            where id = %s
            returning id
            """,
            (next_step["step_key"], user_id, run_id),
        ).fetchone()
    return conn.execute(
        """
        update ai_workflow_runs
        set status = 'ready', approved_by = %s, approved_at = now(), updated_at = now()
        where id = %s
        returning id
        """,
        (user_id, run_id),
    ).fetchone()


def list_runs(conn, organization_id: UUID, limit: int = 50):
    return conn.execute(
        """
        select r.id, r.definition_id, d.slug as definition_slug,
          d.name as definition_name, d.version as definition_version,
          r.workspace_id, r.status, r.idempotency_key, r.input, r.output,
          r.current_step_key, r.estimated_cost_cents, r.actual_cost_cents,
          r.currency, r.approved_at, r.started_at, r.finished_at, r.created_at
        from ai_workflow_runs r
        join ai_workflow_definitions d on d.id = r.definition_id
        where r.organization_id = %s
        order by r.created_at desc
        limit %s
        """,
        (organization_id, limit),
    ).fetchall()


def list_run_steps(conn, run_ids: list[UUID]):
    if not run_ids:
        return []
    return conn.execute(
        """
        select id, run_id, step_key, position, name, description, interactive, status,
          task_kind, capability, provider, model, account_id, model_catalog_id,
          selection_reason, attempts, output, cost_cents, started_at, finished_at
        from ai_workflow_step_runs
        where run_id = any(%s)
        order by run_id, position
        """,
        (run_ids,),
    ).fetchall()


def get_run(conn, organization_id: UUID, run_id: UUID):
    rows = conn.execute(
        """
        select r.id, r.definition_id, d.slug as definition_slug,
          d.name as definition_name, d.version as definition_version,
          r.workspace_id, r.status, r.idempotency_key, r.input, r.output,
          r.current_step_key, r.estimated_cost_cents, r.actual_cost_cents,
          r.currency, r.approved_at, r.started_at, r.finished_at, r.created_at
        from ai_workflow_runs r
        join ai_workflow_definitions d on d.id = r.definition_id
        where r.id = %s and r.organization_id = %s
        """,
        (run_id, organization_id),
    ).fetchall()
    return rows[0] if rows else None


def complete_step(
    conn,
    organization_id: UUID,
    run_id: UUID,
    step_key: str,
    payload: dict[str, Any],
):
    run = get_run(conn, organization_id, run_id)
    if not run or run["status"] not in {"ready", "running"} or run["current_step_key"] != step_key:
        return None
    step = conn.execute(
        """
        update ai_workflow_step_runs
        set status = 'completed', provider = %s, model = %s, output = %s,
          cost_cents = %s, started_at = coalesce(started_at, now()),
          finished_at = now(), updated_at = now()
        where run_id = %s and step_key = %s and status in ('pending', 'running', 'waiting_approval')
        returning id, position
        """,
        (
            payload.get("provider"),
            payload.get("model"),
            Jsonb(payload.get("output", {})),
            payload.get("cost_cents"),
            run_id,
            step_key,
        ),
    ).fetchone()
    if not step:
        return None
    next_step = conn.execute(
        """
        select step_key, interactive
        from ai_workflow_step_runs
        where run_id = %s and position > %s and status = 'pending'
        order by position
        limit 1
        """,
        (run_id, step["position"]),
    ).fetchone()
    added_cost = payload.get("cost_cents") or 0
    if next_step:
        conn.execute(
            """
            update ai_workflow_runs
            set status = 'ready', current_step_key = %s,
              started_at = coalesce(started_at, now()),
              actual_cost_cents = actual_cost_cents + %s, updated_at = now()
            where id = %s
            """,
            (next_step["step_key"], added_cost, run_id),
        )
    else:
        conn.execute(
            """
            update ai_workflow_runs
            set status = 'completed', current_step_key = null, output = %s,
              started_at = coalesce(started_at, now()), finished_at = now(),
              actual_cost_cents = actual_cost_cents + %s, updated_at = now()
            where id = %s
            """,
            (Jsonb(payload.get("output", {})), added_cost, run_id),
        )
    return step
