from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb


def list_accounts(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, subscription_id, provider, channel, display_name, auth_mode,
          execution_mode, auth_ref, status, is_default, capabilities, settings,
          health_detail, last_probe_at,
          exists (
            select 1 from ai_provider_credentials credential
            where credential.account_id = account.id
          ) as credentials_configured,
          created_at, updated_at
        from ai_provider_accounts account
        where organization_id = %s
        order by is_default desc, provider, channel, display_name
        """,
        (organization_id,),
    ).fetchall()


def list_copilot_candidates(conn, organization_id: UUID):
    """Contas + modelos habilitados para o copiloto usar a cota da assinatura.

    Mesma forma que `storage.list_ai_route_candidates` do worker (que serve os
    workflows), para `rank_candidates` conseguir ordenar as duas com o mesmo
    código. `task_kind = 'reasoning'`: o copiloto interpreta e decide.

    Contas de `manual_handoff` ficam de fora — por definição elas exigem um
    humano no meio, e o copiloto responde na hora. O Antigravity CLI pode entrar
    quando cadastrado como `local_cli`, pois hoje possui modo headless oficial.
    """
    return conn.execute(
        """
        select account.id as account_id, account.provider, account.channel,
          account.display_name as account_name, account.auth_mode,
          account.execution_mode, account.auth_ref, account.status as account_status,
          account.capabilities as account_capabilities, account.settings as account_settings,
          credential.encrypted_bundle as credential_bundle,
          model.id as model_catalog_id, model.model_id, model.display_name as model_name,
          model.capability_tier, model.capabilities as model_capabilities,
          model.quality_score, model.cost_score, model.latency_score, model.priority,
          policy.id as policy_id, policy.allowed_channels, policy.allowed_models,
          policy.preferred_tiers, policy.quality_weight, policy.quota_weight,
          policy.cost_weight, policy.reliability_weight, policy.latency_weight,
          policy.minimum_quota_headroom, policy.requires_human_approval,
          policy.allow_fallback,
          (model.id = harness.planner_model_catalog_id) as role_preferred,
          coalesce((
            select jsonb_agg(latest_quota.payload order by latest_quota.bucket_key)
            from (
              select distinct on (quota.bucket_key, coalesce(quota.model_id, ''))
                quota.bucket_key,
                jsonb_build_object(
                  'bucket_key', quota.bucket_key,
                  'model_id', quota.model_id,
                  'remaining_percent', quota.remaining_percent,
                  'resets_at', quota.resets_at,
                  'confidence', quota.confidence,
                  'measured_at', quota.measured_at
                ) as payload
              from ai_quota_buckets quota
              where quota.account_id = account.id
              order by quota.bucket_key, coalesce(quota.model_id, ''), quota.measured_at desc
            ) latest_quota
          ), '[]'::jsonb) as quota_buckets
        from ai_provider_accounts account
        join ai_model_catalog model on model.account_id = account.id and model.enabled
        left join ai_routing_policies policy
          on policy.organization_id = account.organization_id
          and policy.task_kind = 'reasoning'
          and policy.status = 'active'
        left join ai_harness_configs harness
          on harness.organization_id = account.organization_id
        left join ai_provider_credentials credential on credential.account_id = account.id
        where account.organization_id = %s
          and account.status in ('active', 'degraded')
          and account.execution_mode <> 'manual_handoff'
        order by model.priority, account.display_name, model.display_name
        """,
        (organization_id,),
    ).fetchall()


def list_models(conn, organization_id: UUID):
    return conn.execute(
        """
        select m.id, m.account_id, m.model_id, m.display_name, m.family,
          m.capability_tier, m.capabilities, m.quality_score, m.cost_score,
          m.latency_score, m.context_window, m.enabled, m.priority, m.metadata,
          m.discovered_at, m.created_at, m.updated_at
        from ai_model_catalog m
        join ai_provider_accounts a on a.id = m.account_id
        where a.organization_id = %s
        order by a.provider, a.channel, m.priority, m.display_name
        """,
        (organization_id,),
    ).fetchall()


def list_latest_quota_buckets(conn, organization_id: UUID):
    return conn.execute(
        """
        select distinct on (q.account_id, q.bucket_key, coalesce(q.model_id, ''))
          q.id, q.account_id, q.bucket_key, q.scope, q.model_id, q.total_units,
          q.used_units, q.used_percent, q.remaining_percent, q.unit,
          q.window_duration_minutes, q.resets_at, q.source, q.confidence,
          q.measured_at, q.raw_metadata, q.notes
        from ai_quota_buckets q
        join ai_provider_accounts a on a.id = q.account_id
        where a.organization_id = %s
        order by q.account_id, q.bucket_key, coalesce(q.model_id, ''), q.measured_at desc
        """,
        (organization_id,),
    ).fetchall()


def latest_quota_for_account(conn, account_id: UUID):
    """Cota mais recente de UMA conta — o que a trilha do copiloto mostra por
    execução roteada. Mesma consulta de `list_latest_quota_buckets`, restrita a
    uma conta: cota é estado atual, não é lido a partir do histórico de runs."""
    return conn.execute(
        """
        select distinct on (q.bucket_key, coalesce(q.model_id, ''))
          q.id, q.account_id, q.bucket_key, q.scope, q.model_id, q.total_units,
          q.used_units, q.used_percent, q.remaining_percent, q.unit,
          q.window_duration_minutes, q.resets_at, q.source, q.confidence,
          q.measured_at, q.raw_metadata, q.notes
        from ai_quota_buckets q
        where q.account_id = %s
        order by q.bucket_key, coalesce(q.model_id, ''), q.measured_at desc
        """,
        (account_id,),
    ).fetchall()


def get_account(conn, account_id: UUID):
    return conn.execute(
        """
        select account.id, account.organization_id, account.provider, account.channel,
          account.display_name, account.auth_mode, account.execution_mode,
          account.auth_ref, account.status, account.capabilities, account.settings,
          credential.encrypted_bundle as credential_bundle,
          credential.auth_method as stored_auth_method
        from ai_provider_accounts account
        left join ai_provider_credentials credential on credential.account_id = account.id
        where account.id = %s
        """,
        (account_id,),
    ).fetchone()


def create_login_session(conn, organization_id: UUID, account_id: UUID, user_id: UUID):
    account = conn.execute(
        """
        select id
        from ai_provider_accounts
        where id = %s and organization_id = %s
          and channel in ('codex_chatgpt', 'claude_code', 'antigravity_cli')
        for update
        """,
        (account_id, organization_id),
    ).fetchone()
    if not account:
        return None, []
    canceled = conn.execute(
        """
        update ai_provider_login_sessions
        set status = 'canceled', encrypted_pending_input = null,
          error_message = 'Substituída por uma nova tentativa de login.',
          finished_at = now(), updated_at = now()
        where account_id = %s and organization_id = %s
          and status in ('pending', 'running', 'waiting_input')
        returning id
        """,
        (account_id, organization_id),
    ).fetchall()
    row = conn.execute(
        """
        insert into ai_provider_login_sessions (organization_id, account_id, requested_by)
        values (%s, %s, %s)
        returning id, organization_id, account_id, status, public_output,
          prompt_hint, error_message, expires_at, started_at, finished_at,
          created_at, updated_at
        """,
        (organization_id, account_id, user_id),
    ).fetchone()
    return row, [item["id"] for item in canceled]


def get_login_session(conn, organization_id: UUID, session_id: UUID):
    return conn.execute(
        """
        select session.id, session.organization_id, session.account_id,
          account.channel, account.display_name as account_name,
          session.status, session.public_output, session.prompt_hint,
          session.error_message, session.expires_at, session.started_at,
          session.finished_at, session.created_at, session.updated_at
        from ai_provider_login_sessions session
        join ai_provider_accounts account on account.id = session.account_id
        where session.id = %s and session.organization_id = %s
        """,
        (session_id, organization_id),
    ).fetchone()


def queue_login_input(conn, organization_id: UUID, session_id: UUID, encrypted_input: str) -> bool:
    row = conn.execute(
        """
        update ai_provider_login_sessions
        set encrypted_pending_input = %s, status = 'running', updated_at = now()
        where id = %s and organization_id = %s
          and status in ('pending', 'running', 'waiting_input')
          and expires_at > now()
        returning id
        """,
        (encrypted_input, session_id, organization_id),
    ).fetchone()
    return bool(row)


def cancel_login_session(conn, organization_id: UUID, session_id: UUID) -> bool:
    row = conn.execute(
        """
        update ai_provider_login_sessions
        set status = 'canceled', encrypted_pending_input = null,
          finished_at = now(), updated_at = now()
        where id = %s and organization_id = %s
          and status in ('pending', 'running', 'waiting_input')
        returning id
        """,
        (session_id, organization_id),
    ).fetchone()
    return bool(row)


def disconnect_provider_credentials(conn, organization_id: UUID, account_id: UUID, user_id: UUID) -> bool:
    account = conn.execute(
        """
        select id
        from ai_provider_accounts
        where id = %s and organization_id = %s
          and channel in ('codex_chatgpt', 'claude_code', 'antigravity_cli')
        for update
        """,
        (account_id, organization_id),
    ).fetchone()
    if not account:
        return False
    conn.execute(
        """
        update ai_provider_login_sessions
        set status = 'canceled', encrypted_pending_input = null,
          error_message = 'Credencial desconectada do Bioma.',
          finished_at = now(), updated_at = now()
        where account_id = %s and organization_id = %s
          and status in ('pending', 'running', 'waiting_input')
        """,
        (account_id, organization_id),
    )
    conn.execute("delete from ai_provider_credentials where account_id = %s", (account_id,))
    conn.execute(
        """
        update ai_provider_accounts
        set status = 'unavailable', auth_ref = null,
          health_detail = 'Credencial desconectada do Bioma.',
          updated_by = %s, updated_at = now()
        where id = %s
        """,
        (user_id, account_id),
    )
    return True


def record_runtime_probe(
    conn,
    organization_id: UUID,
    account_id: UUID,
    result: dict[str, Any],
) -> bool:
    row = conn.execute(
        """
        update ai_provider_accounts
        set status = case
            when status in ('paused', 'unavailable') then status
            when %s then 'active'
            else 'degraded'
          end,
          health_detail = %s, last_probe_at = now(), updated_at = now()
        where id = %s and organization_id = %s
        returning id
        """,
        (result["ready"], result["detail"][:2000], account_id, organization_id),
    ).fetchone()
    return bool(row)


def list_policies(conn, organization_id: UUID):
    return conn.execute(
        """
        select id, task_kind, capability, name, allowed_channels, allowed_models,
          preferred_tiers, quality_weight, quota_weight, cost_weight,
          reliability_weight, latency_weight, minimum_quota_headroom,
          requires_human_approval, allow_fallback, status, created_at, updated_at
        from ai_routing_policies
        where organization_id = %s
        order by status = 'active' desc, task_kind
        """,
        (organization_id,),
    ).fetchall()


def get_harness_config(conn, organization_id: UUID):
    return conn.execute(
        """
        select organization_id, planner_model_catalog_id,
          tool_caller_model_catalog_id, auditor_model_catalog_id,
          curator_model_catalog_id, enabled_tools, created_at, updated_at
        from ai_harness_configs
        where organization_id = %s
        """,
        (organization_id,),
    ).fetchone()


def upsert_harness_config(
    conn,
    organization_id: UUID,
    user_id: UUID,
    payload: dict[str, Any],
):
    model_ids = [
        payload.get("planner_model_catalog_id"),
        payload.get("tool_caller_model_catalog_id"),
        payload.get("auditor_model_catalog_id"),
        payload.get("curator_model_catalog_id"),
    ]
    selected = [model_id for model_id in model_ids if model_id]
    if selected:
        count = conn.execute(
            """
            select count(*) as count
            from ai_model_catalog model
            join ai_provider_accounts account on account.id = model.account_id
            where account.organization_id = %s and model.id = any(%s)
            """,
            (organization_id, selected),
        ).fetchone()["count"]
        if count != len(set(selected)):
            return None
    return conn.execute(
        """
        insert into ai_harness_configs (
          organization_id, planner_model_catalog_id, tool_caller_model_catalog_id,
          auditor_model_catalog_id, curator_model_catalog_id, enabled_tools,
          created_by, updated_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (organization_id) do update set
          planner_model_catalog_id = excluded.planner_model_catalog_id,
          tool_caller_model_catalog_id = excluded.tool_caller_model_catalog_id,
          auditor_model_catalog_id = excluded.auditor_model_catalog_id,
          curator_model_catalog_id = excluded.curator_model_catalog_id,
          enabled_tools = excluded.enabled_tools,
          updated_by = excluded.updated_by,
          updated_at = now()
        returning organization_id
        """,
        (
            organization_id,
            payload.get("planner_model_catalog_id"),
            payload.get("tool_caller_model_catalog_id"),
            payload.get("auditor_model_catalog_id"),
            payload.get("curator_model_catalog_id"),
            payload.get("enabled_tools") or [],
            user_id,
            user_id,
        ),
    ).fetchone()


def list_quota_collection_jobs(conn, organization_id: UUID, limit: int = 30):
    return conn.execute(
        """
        select id, account_id, collector, status, result, error_message, attempts,
          started_at, finished_at, created_at
        from ai_quota_collection_jobs
        where organization_id = %s
        order by created_at desc
        limit %s
        """,
        (organization_id, limit),
    ).fetchall()


def enqueue_quota_collection(conn, organization_id: UUID, account_id: UUID, user_id: UUID):
    return conn.execute(
        """
        insert into ai_quota_collection_jobs (
          organization_id, account_id, requested_by, collector
        )
        select %s, account.id, %s,
          case account.channel
            when 'codex_chatgpt' then 'codex_app_server'
            when 'claude_code' then 'claude_statusline'
            when 'antigravity_cli' then 'antigravity_usage'
          end
        from ai_provider_accounts account
        where account.id = %s and account.organization_id = %s
          and account.channel in ('codex_chatgpt', 'claude_code', 'antigravity_cli')
        returning id
        """,
        (organization_id, user_id, account_id, organization_id),
    ).fetchone()


def create_account(conn, organization_id: UUID, user_id: UUID, payload: dict[str, Any]):
    if payload.get("is_default"):
        conn.execute(
            """
            update ai_provider_accounts
            set is_default = false, updated_at = now(), updated_by = %s
            where organization_id = %s and channel = %s and is_default
            """,
            (user_id, organization_id, payload["channel"]),
        )
    return conn.execute(
        """
        insert into ai_provider_accounts (
          organization_id, subscription_id, provider, channel, display_name,
          auth_mode, execution_mode, auth_ref, status, is_default, capabilities,
          settings, created_by, updated_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            organization_id,
            payload.get("subscription_id"),
            payload["provider"],
            payload["channel"],
            payload["display_name"],
            payload["auth_mode"],
            payload["execution_mode"],
            payload.get("auth_ref"),
            payload["status"],
            payload["is_default"],
            payload["capabilities"],
            Jsonb(payload["settings"]),
            user_id,
            user_id,
        ),
    ).fetchone()


def update_account(
    conn,
    organization_id: UUID,
    account_id: UUID,
    user_id: UUID,
    payload: dict[str, Any],
) -> bool:
    current = conn.execute(
        """
        select channel from ai_provider_accounts
        where id = %s and organization_id = %s
        """,
        (account_id, organization_id),
    ).fetchone()
    if not current:
        return False
    if payload.get("is_default"):
        conn.execute(
            """
            update ai_provider_accounts
            set is_default = false, updated_at = now(), updated_by = %s
            where organization_id = %s and channel = %s and id <> %s and is_default
            """,
            (user_id, organization_id, current["channel"], account_id),
        )
    allowed = {
        "subscription_id",
        "display_name",
        "auth_mode",
        "execution_mode",
        "auth_ref",
        "status",
        "is_default",
        "capabilities",
        "settings",
    }
    assignments = []
    values: list[Any] = []
    for key, value in payload.items():
        if key not in allowed:
            continue
        assignments.append(f"{key} = %s")
        values.append(Jsonb(value) if key == "settings" else value)
    if not assignments:
        return True
    values.extend([user_id, account_id, organization_id])
    row = conn.execute(
        f"""
        update ai_provider_accounts
        set {", ".join(assignments)}, updated_by = %s, updated_at = now()
        where id = %s and organization_id = %s
        returning id
        """,
        values,
    ).fetchone()
    return bool(row)


def upsert_model(
    conn,
    organization_id: UUID,
    account_id: UUID,
    payload: dict[str, Any],
):
    return conn.execute(
        """
        insert into ai_model_catalog (
          account_id, model_id, display_name, family, capability_tier,
          capabilities, quality_score, cost_score, latency_score, context_window,
          enabled, priority, metadata, discovered_at
        )
        select a.id, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
        from ai_provider_accounts a
        where a.id = %s and a.organization_id = %s
        on conflict (account_id, model_id) do update set
          display_name = excluded.display_name,
          family = excluded.family,
          capability_tier = excluded.capability_tier,
          capabilities = excluded.capabilities,
          quality_score = excluded.quality_score,
          cost_score = excluded.cost_score,
          latency_score = excluded.latency_score,
          context_window = excluded.context_window,
          enabled = excluded.enabled,
          priority = excluded.priority,
          metadata = excluded.metadata,
          discovered_at = now(),
          updated_at = now()
        returning id
        """,
        (
            payload["model_id"],
            payload["display_name"],
            payload.get("family"),
            payload["capability_tier"],
            payload["capabilities"],
            payload["quality_score"],
            payload["cost_score"],
            payload["latency_score"],
            payload.get("context_window"),
            payload["enabled"],
            payload["priority"],
            Jsonb(payload["metadata"]),
            account_id,
            organization_id,
        ),
    ).fetchone()


def create_quota_bucket(
    conn,
    organization_id: UUID,
    account_id: UUID,
    user_id: UUID,
    payload: dict[str, Any],
):
    return conn.execute(
        """
        insert into ai_quota_buckets (
          account_id, bucket_key, scope, model_id, total_units, used_units,
          used_percent, remaining_percent, unit, window_duration_minutes,
          resets_at, source, confidence, measured_at, raw_metadata, notes,
          created_by
        )
        select a.id, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          coalesce(%s, now()), %s, %s, %s
        from ai_provider_accounts a
        where a.id = %s and a.organization_id = %s
        returning id
        """,
        (
            payload["bucket_key"],
            payload["scope"],
            payload.get("model_id"),
            payload.get("total_units"),
            payload.get("used_units"),
            payload.get("used_percent"),
            payload.get("remaining_percent"),
            payload["unit"],
            payload.get("window_duration_minutes"),
            payload.get("resets_at"),
            payload["source"],
            payload["confidence"],
            payload.get("measured_at"),
            Jsonb(payload["raw_metadata"]),
            payload.get("notes"),
            user_id,
            account_id,
            organization_id,
        ),
    ).fetchone()


def upsert_policy(conn, organization_id: UUID, user_id: UUID, payload: dict[str, Any]):
    return conn.execute(
        """
        insert into ai_routing_policies (
          organization_id, task_kind, capability, name, allowed_channels,
          allowed_models, preferred_tiers, quality_weight, quota_weight,
          cost_weight, reliability_weight, latency_weight,
          minimum_quota_headroom, requires_human_approval, allow_fallback,
          status, created_by, updated_by
        ) values (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s
        )
        on conflict (organization_id, task_kind) do update set
          capability = excluded.capability,
          name = excluded.name,
          allowed_channels = excluded.allowed_channels,
          allowed_models = excluded.allowed_models,
          preferred_tiers = excluded.preferred_tiers,
          quality_weight = excluded.quality_weight,
          quota_weight = excluded.quota_weight,
          cost_weight = excluded.cost_weight,
          reliability_weight = excluded.reliability_weight,
          latency_weight = excluded.latency_weight,
          minimum_quota_headroom = excluded.minimum_quota_headroom,
          requires_human_approval = excluded.requires_human_approval,
          allow_fallback = excluded.allow_fallback,
          status = excluded.status,
          updated_by = excluded.updated_by,
          updated_at = now()
        returning id
        """,
        (
            organization_id,
            payload["task_kind"],
            payload["capability"],
            payload["name"],
            payload["allowed_channels"],
            payload["allowed_models"],
            payload["preferred_tiers"],
            payload["quality_weight"],
            payload["quota_weight"],
            payload["cost_weight"],
            payload["reliability_weight"],
            payload["latency_weight"],
            payload["minimum_quota_headroom"],
            payload["requires_human_approval"],
            payload["allow_fallback"],
            payload["status"],
            user_id,
            user_id,
        ),
    ).fetchone()
