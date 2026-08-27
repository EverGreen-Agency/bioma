from typing import Any
from uuid import UUID
from datetime import date
import json

from psycopg import sql
from psycopg.types.json import Jsonb


def _json_safe(value):
    return json.loads(json.dumps(value, default=str))


def next_job_type(conn) -> str | None:
    row = conn.execute(
        """
        select job_type
        from (
          select 'ai_content' as job_type, created_at as queued_at
          from ai_content_requests where status = 'queued'
          union all
          select 'performance' as job_type, started_at as queued_at
          from sync_runs where source = 'performance' and status = 'queued'
          union all
          select 'ai_workflow' as job_type, run.created_at as queued_at
          from ai_workflow_runs run
          join ai_workflow_step_runs step
            on step.run_id = run.id and step.step_key = run.current_step_key
          where run.status in ('ready', 'running') and step.status = 'pending'
          union all
          select 'ai_quota' as job_type, created_at as queued_at
          from ai_quota_collection_jobs where status = 'queued'
        ) jobs
        order by queued_at
        limit 1
        """
    ).fetchone()
    return row["job_type"] if row else None


def claim_next_sync(conn):
    return conn.execute(
        """
        with candidate as (
          select id
          from sync_runs
          where source = 'performance' and status = 'queued'
          order by started_at asc
          for update skip locked
          limit 1
        )
        update sync_runs run
        set status = 'running', error_code = null, error_message = null,
            heartbeat_at = now(), attempts = run.attempts + 1
        from candidate
        where run.id = candidate.id
        -- `workspace_id` e obrigatorio aqui desde a 0087: a conexao pertence
        -- ao workspace, e o orquestrador lista por ele. Sem esta coluna no
        -- returning, `run_next_sync` estoura com KeyError — que foi
        -- exatamente o que aconteceu e so o smoke com banco isolado pegou.
        returning run.id, run.client_id, run.workspace_id, run.organization_id, run.provider,
                  run.date_from, run.date_to, run.started_at, run.attempts
        """
    ).fetchone()


def claim_next_ai_content(conn):
    return conn.execute(
        """
        with next_request as (
          select id
          from ai_content_requests
          where status = 'queued'
          order by created_at
          for update skip locked
          limit 1
        )
        update ai_content_requests request
        set status = 'running', started_at = now(), updated_at = now(),
            heartbeat_at = now(), attempts = request.attempts + 1
        from next_request
        where request.id = next_request.id
        returning request.id, request.workspace_id, request.organization_id,
          request.requested_by, request.brief, request.channels, request.quantity,
          request.tone, request.objective, request.methodology_refs, request.attempts
        """
    ).fetchone()


def claim_next_ai_workflow(conn):
    return conn.execute(
        """
        with candidate as (
          select step.id
          from ai_workflow_step_runs step
          join ai_workflow_runs run on run.id = step.run_id
          where run.status in ('ready', 'running')
            and step.status = 'pending'
            and step.step_key = run.current_step_key
          order by run.created_at, step.position
          for update of step skip locked
          limit 1
        )
        update ai_workflow_step_runs step
        set status = 'running', started_at = coalesce(step.started_at, now()),
          heartbeat_at = now(), attempts = step.attempts + 1, updated_at = now()
        from candidate, ai_workflow_runs run, ai_workflow_definitions definition
        where step.id = candidate.id
          and run.id = step.run_id
          and definition.id = run.definition_id
        returning step.id as step_run_id, step.run_id, step.step_key, step.position,
          step.name, step.description, step.interactive, step.task_kind, step.capability,
          step.attempts, run.organization_id, run.workspace_id, run.requested_by,
          run.input as workflow_input, run.currency, definition.slug as definition_slug,
          definition.name as definition_name,
          coalesce((
            select jsonb_object_agg(previous.step_key, previous.output)
            from ai_workflow_step_runs previous
            where previous.run_id = run.id
              and previous.position < step.position
              and previous.output is not null
          ), '{}'::jsonb) as previous_outputs
        """
    ).fetchone()


def claim_next_ai_quota_collection(conn):
    return conn.execute(
        """
        with candidate as (
          select id
          from ai_quota_collection_jobs
          where status = 'queued'
          order by created_at
          for update skip locked
          limit 1
        )
        update ai_quota_collection_jobs job
        set status = 'running', attempts = job.attempts + 1, started_at = now(),
          heartbeat_at = now(), updated_at = now()
        from candidate, ai_provider_accounts account
        where job.id = candidate.id and account.id = job.account_id
        returning job.id, job.organization_id, job.account_id, job.collector,
          job.attempts, account.channel, account.settings,
          (select encrypted_bundle from ai_provider_credentials where account_id = account.id) as credential_bundle
        """
    ).fetchone()


def complete_ai_quota_collection(conn, job: dict, buckets: list[dict]) -> None:
    for bucket in buckets:
        conn.execute(
            """
            insert into ai_quota_buckets (
              account_id, bucket_key, scope, model_id, total_units, used_units,
              used_percent, remaining_percent, unit, window_duration_minutes,
              resets_at, source, confidence, measured_at, raw_metadata, notes
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                job["account_id"],
                bucket["bucket_key"],
                bucket["scope"],
                bucket.get("model_id"),
                bucket.get("total_units"),
                bucket.get("used_units"),
                bucket.get("used_percent"),
                bucket.get("remaining_percent"),
                bucket["unit"],
                bucket.get("window_duration_minutes"),
                bucket.get("resets_at"),
                bucket["source"],
                bucket["confidence"],
                bucket["measured_at"],
                Jsonb(bucket.get("raw_metadata") or {}),
                bucket.get("notes"),
            ),
        )
    conn.execute(
        """
        update ai_quota_collection_jobs
        set status = 'completed', result = %s, error_message = null,
          heartbeat_at = null, finished_at = now(), updated_at = now()
        where id = %s
        """,
        (Jsonb({"buckets_recorded": len(buckets)}), job["id"]),
    )
    conn.execute(
        """
        update ai_provider_accounts
        set status = case when status = 'degraded' then 'active' else status end,
          health_detail = null, last_probe_at = now(), updated_at = now()
        where id = %s
        """,
        (job["account_id"],),
    )


def fail_ai_quota_collection(conn, job: dict, message: str) -> None:
    conn.execute(
        """
        update ai_quota_collection_jobs
        set status = 'failed', error_message = %s, heartbeat_at = null,
          finished_at = now(), updated_at = now()
        where id = %s
        """,
        (message[:2000], job["id"]),
    )
    conn.execute(
        """
        update ai_provider_accounts
        set status = case when status = 'active' then 'degraded' else status end,
          health_detail = %s, last_probe_at = now(), updated_at = now()
        where id = %s
        """,
        (message[:2000], job["account_id"]),
    )


def list_ai_route_candidates(conn, job: dict):
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
          (model.id = case %s
            when 'reasoning' then harness.planner_model_catalog_id
            when 'tool_calling' then harness.tool_caller_model_catalog_id
            when 'quality_audit' then harness.auditor_model_catalog_id
            when 'knowledge_curation' then harness.curator_model_catalog_id
            else null
          end) as role_preferred,
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
          and policy.task_kind = %s
          and policy.status = 'active'
        left join ai_harness_configs harness
          on harness.organization_id = account.organization_id
        left join ai_provider_credentials credential on credential.account_id = account.id
        where account.organization_id = %s
          and account.status in ('active', 'degraded')
        order by model.priority, account.display_name, model.display_name
        """,
        (job["task_kind"], job["task_kind"], job["organization_id"]),
    ).fetchall()


def start_ai_execution_attempt(conn, job: dict, candidate: dict):
    row = conn.execute(
        """
        insert into ai_execution_attempts (
          organization_id, workflow_run_id, step_run_id, account_id, model_catalog_id,
          attempt_number, status, selection_score, selection_reason, quota_before,
          input, started_at
        )
        values (
          %s, %s, %s, %s, %s,
          coalesce((select max(attempt_number) + 1 from ai_execution_attempts where step_run_id = %s), 1),
          'running', %s, %s, %s, %s, now()
        )
        returning id, attempt_number
        """,
        (
            job["organization_id"],
            job["run_id"],
            job["step_run_id"],
            candidate["account_id"],
            candidate["model_catalog_id"],
            job["step_run_id"],
            candidate["score"],
            Jsonb({"reasons": candidate["reasons"], "task_kind": job["task_kind"]}),
            Jsonb(_json_safe(candidate.get("quota_buckets") or [])),
            Jsonb(
                {
                    "workflow_input": job["workflow_input"],
                    "previous_outputs": job["previous_outputs"],
                    "step_key": job["step_key"],
                }
            ),
        ),
    ).fetchone()
    conn.execute(
        """
        update ai_workflow_step_runs
        set routing_policy_id = %s, account_id = %s, model_catalog_id = %s,
          provider = %s, model = %s, selection_reason = %s, updated_at = now()
        where id = %s
        """,
        (
            candidate.get("policy_id"),
            candidate["account_id"],
            candidate["model_catalog_id"],
            candidate["provider"],
            candidate["model_id"],
            Jsonb({"score": str(candidate["score"]), "reasons": candidate["reasons"]}),
            job["step_run_id"],
        ),
    )
    return row


def fail_ai_execution_attempt(conn, attempt_id, message: str) -> None:
    conn.execute(
        """
        update ai_execution_attempts
        set status = 'failed', error_code = 'PROVIDER_EXECUTION_FAILED',
          error_message = %s, finished_at = now()
        where id = %s
        """,
        (message[:2000], attempt_id),
    )


def complete_ai_workflow_step(conn, job: dict, candidate: dict, attempt_id, result: dict) -> None:
    output = {"text": result["text"], "provider_metadata": result.get("metadata", {})}
    usage = result.get("usage") or {}
    conn.execute(
        """
        update ai_execution_attempts
        set status = 'completed', output = %s, input_units = %s, output_units = %s,
          cached_units = %s, cost_cents = %s, currency = upper(%s), latency_ms = %s,
          external_event_id = %s, finished_at = now()
        where id = %s
        """,
        (
            Jsonb(output),
            usage.get("input_units"),
            usage.get("output_units"),
            usage.get("cached_units"),
            result.get("cost_cents"),
            result.get("currency", "USD"),
            result.get("latency_ms"),
            result.get("external_event_id"),
            attempt_id,
        ),
    )
    next_status = "waiting_approval" if job["interactive"] else "completed"
    conn.execute(
        """
        update ai_workflow_step_runs
        set status = %s, output = %s, cost_cents = %s,
          finished_at = case when %s = 'completed' then now() else null end,
          heartbeat_at = null, updated_at = now()
        where id = %s
        """,
        (next_status, Jsonb(output), result.get("cost_cents"), next_status, job["step_run_id"]),
    )
    if result.get("external_event_id") or any(value is not None for value in usage.values()):
        conn.execute(
            """
            insert into ai_usage_events (
              organization_id, workspace_id, workflow_run_id, user_id, provider,
              model, source, external_event_id, input_units, output_units,
              cached_units, unit, cost_cents, currency, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              'tokens', %s, upper(%s), %s)
            on conflict (organization_id, provider, external_event_id)
              where external_event_id is not null
            do update set metadata = ai_usage_events.metadata || excluded.metadata
            """,
            (
                job["organization_id"],
                job["workspace_id"],
                job["run_id"],
                job["requested_by"],
                candidate["provider"],
                candidate["model_id"],
                f"workflow:{job['definition_slug']}:{job['step_key']}",
                result.get("external_event_id"),
                usage.get("input_units"),
                usage.get("output_units"),
                usage.get("cached_units"),
                result.get("cost_cents"),
                result.get("currency", "USD"),
                Jsonb(
                    {
                        "execution_attempt_id": str(attempt_id),
                        "channel": candidate["channel"],
                        "cost_status": "known" if result.get("cost_cents") is not None else "unknown",
                    }
                ),
            ),
        )
    added_cost = result.get("cost_cents") or 0
    if job["interactive"]:
        conn.execute(
            """
            update ai_workflow_runs
            set status = 'pending_approval', started_at = coalesce(started_at, now()),
              actual_cost_cents = actual_cost_cents + %s, updated_at = now()
            where id = %s
            """,
            (added_cost, job["run_id"]),
        )
        return
    next_step = conn.execute(
        """
        select step_key
        from ai_workflow_step_runs
        where run_id = %s and position > %s and status = 'pending'
        order by position
        limit 1
        """,
        (job["run_id"], job["position"]),
    ).fetchone()
    if next_step:
        conn.execute(
            """
            update ai_workflow_runs
            set status = 'ready', current_step_key = %s,
              started_at = coalesce(started_at, now()),
              actual_cost_cents = actual_cost_cents + %s, updated_at = now()
            where id = %s
            """,
            (next_step["step_key"], added_cost, job["run_id"]),
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
            (Jsonb(output), added_cost, job["run_id"]),
        )


def fail_ai_workflow_step(conn, job: dict, message: str) -> None:
    conn.execute(
        """
        update ai_workflow_step_runs
        set status = 'failed', heartbeat_at = null, finished_at = now(), updated_at = now()
        where id = %s
        """,
        (job["step_run_id"],),
    )
    conn.execute(
        """
        update ai_workflow_runs
        set status = 'failed', finished_at = now(), updated_at = now(),
          output = %s
        where id = %s
        """,
        (Jsonb({"error": message[:2000], "step_key": job["step_key"]}), job["run_id"]),
    )


def heartbeat_sync(conn, sync_id: UUID) -> None:
    """Renova o lease de um sync em andamento.

    Chamado entre providers: uma janela de 30 dias em quatro providers passa
    do lease default, e sem isso o reaper reenfileiraria um job que está vivo.
    """
    conn.execute(
        "update sync_runs set heartbeat_at = now() where id = %s and status = 'running'",
        (sync_id,),
    )


def reclaim_stalled_jobs(conn, lease_seconds: int, max_attempts: int) -> dict[str, int]:
    """Devolve à fila (ou encerra como erro) jobs cujo lease expirou.

    Um job perde o lease quando o worker morre sem completá-lo. Enquanto tiver
    tentativa disponível ele volta para `queued`; ao estourar `max_attempts`
    vira `error` com código próprio, para não reprocessar em loop um job que
    derruba o worker toda vez.
    """
    requeued_syncs = conn.execute(
        """
        update sync_runs
        set status = 'queued', heartbeat_at = null,
            error_code = null, error_message = null
        where status = 'running'
          and heartbeat_at < now() - make_interval(secs => %s)
          and attempts < %s
        returning id
        """,
        (lease_seconds, max_attempts),
    ).fetchall()

    failed_syncs = conn.execute(
        """
        update sync_runs
        set status = 'error', heartbeat_at = null, finished_at = now(),
            error_code = 'JOB_STALLED',
            error_message = 'Job excedeu o lease sem concluir e esgotou as tentativas.'
        where status = 'running'
          and heartbeat_at < now() - make_interval(secs => %s)
          and attempts >= %s
        returning id
        """,
        (lease_seconds, max_attempts),
    ).fetchall()

    requeued_ai = conn.execute(
        """
        update ai_content_requests
        set status = 'queued', heartbeat_at = null, error_message = null,
            updated_at = now()
        where status = 'running'
          and heartbeat_at < now() - make_interval(secs => %s)
          and attempts < %s
        returning id
        """,
        (lease_seconds, max_attempts),
    ).fetchall()

    failed_ai = conn.execute(
        """
        update ai_content_requests
        set status = 'error', heartbeat_at = null, finished_at = now(),
            updated_at = now(),
            error_message = 'Job excedeu o lease sem concluir e esgotou as tentativas.'
        where status = 'running'
          and heartbeat_at < now() - make_interval(secs => %s)
          and attempts >= %s
        returning id
        """,
        (lease_seconds, max_attempts),
    ).fetchall()

    requeued_workflows = conn.execute(
        """
        with stalled as (
          update ai_workflow_step_runs
          set status = 'pending', heartbeat_at = null, updated_at = now()
          where status = 'running'
            and heartbeat_at < now() - make_interval(secs => %s)
            and attempts < %s
          returning run_id
        )
        update ai_workflow_runs run
        set status = 'ready', updated_at = now()
        from stalled
        where run.id = stalled.run_id
        returning run.id
        """,
        (lease_seconds, max_attempts),
    ).fetchall()

    failed_workflows = conn.execute(
        """
        with stalled as (
          update ai_workflow_step_runs
          set status = 'failed', heartbeat_at = null, finished_at = now(), updated_at = now()
          where status = 'running'
            and heartbeat_at < now() - make_interval(secs => %s)
            and attempts >= %s
          returning run_id, step_key
        )
        update ai_workflow_runs run
        set status = 'failed', finished_at = now(), updated_at = now(),
          output = jsonb_build_object(
            'error', 'Job excedeu o lease sem concluir e esgotou as tentativas.',
            'code', 'JOB_STALLED',
            'step_key', stalled.step_key
          )
        from stalled
        where run.id = stalled.run_id
        returning run.id
        """,
        (lease_seconds, max_attempts),
    ).fetchall()

    conn.execute(
        """
        update ai_execution_attempts attempt
        set status = 'failed', error_code = 'JOB_STALLED',
          error_message = 'Execução perdeu o lease antes de concluir.',
          finished_at = now()
        from ai_workflow_step_runs step
        where attempt.step_run_id = step.id
          and attempt.status = 'running'
          and step.status in ('pending', 'failed')
          and step.heartbeat_at is null
        """
    )

    requeued_quota = conn.execute(
        """
        update ai_quota_collection_jobs
        set status = 'queued', heartbeat_at = null, error_message = null, updated_at = now()
        where status = 'running'
          and heartbeat_at < now() - make_interval(secs => %s)
          and attempts < %s
        returning id
        """,
        (lease_seconds, max_attempts),
    ).fetchall()

    failed_quota = conn.execute(
        """
        update ai_quota_collection_jobs
        set status = 'failed', heartbeat_at = null, finished_at = now(), updated_at = now(),
          error_message = 'Job excedeu o lease sem concluir e esgotou as tentativas.'
        where status = 'running'
          and heartbeat_at < now() - make_interval(secs => %s)
          and attempts >= %s
        returning id
        """,
        (lease_seconds, max_attempts),
    ).fetchall()

    return {
        "requeued_syncs": len(requeued_syncs),
        "failed_syncs": len(failed_syncs),
        "requeued_ai_content": len(requeued_ai),
        "failed_ai_content": len(failed_ai),
        "requeued_ai_workflows": len(requeued_workflows),
        "failed_ai_workflows": len(failed_workflows),
        "requeued_ai_quota": len(requeued_quota),
        "failed_ai_quota": len(failed_quota),
    }


def complete_ai_content(conn, request: dict, result: dict) -> None:
    conn.execute(
        """
        update ai_content_requests
        set status = 'ready', provider = %s, model = %s, generation_mode = %s,
          output = %s, error_message = null, finished_at = now(), updated_at = now()
        where id = %s
        """,
        (
            result["provider"],
            result["model"],
            result["generation_mode"],
            Jsonb(result["output"]),
            request["id"],
        ),
    )
    if result.get("generation_mode") == "live":
        usage = result.get("usage") or {}
        input_details = usage.get("input_tokens_details") or {}
        conn.execute(
            """
            insert into ai_usage_events (
              organization_id, workspace_id, user_id, provider, model, source,
              external_event_id, input_units, output_units, cached_units, unit,
              cost_cents, currency, metadata
            )
            values (%s, %s, %s, %s, %s, 'ai_content', %s, %s, %s, %s,
              'tokens', null, 'USD', %s)
            on conflict (organization_id, provider, external_event_id)
              where external_event_id is not null
            do update set metadata = ai_usage_events.metadata || excluded.metadata
            """,
            (
                request["organization_id"],
                request["workspace_id"],
                request["requested_by"],
                result["provider"],
                result["model"],
                result.get("response_id"),
                usage.get("input_tokens"),
                usage.get("output_tokens"),
                input_details.get("cached_tokens"),
                Jsonb(
                    {
                        "content_request_id": str(request["id"]),
                        "usage": usage,
                        "cost_status": "unknown_until_pricing_is_configured",
                    }
                ),
            ),
        )
    conn.execute(
        """
        insert into ai_runs (
          organization_id, workspace_id, user_id, content_request_id,
          provider, model, prompt_version, input_schema, output_schema, status, metadata
        )
        values (%s, %s, %s, %s, %s, %s, 'ai-content-v1',
          'AiContentRequestCreate', 'AiContentOutput', 'ok', %s)
        """,
        (
            request["organization_id"],
            request["workspace_id"],
            request["requested_by"],
            request["id"],
            result["provider"],
            result["model"],
            Jsonb({"generation_mode": result["generation_mode"], "usage": result.get("usage", {})}),
        ),
    )


def fail_ai_content(conn, request: dict, message: str) -> None:
    conn.execute(
        """
        update ai_content_requests
        set status = 'error', error_message = %s, finished_at = now(), updated_at = now()
        where id = %s
        """,
        (message[:2000], request["id"]),
    )
    conn.execute(
        """
        insert into ai_runs (
          organization_id, workspace_id, user_id, content_request_id,
          provider, model, prompt_version, input_schema, output_schema, status, metadata
        )
        values (%s, %s, %s, %s, 'openai', 'unknown', 'ai-content-v1',
          'AiContentRequestCreate', 'AiContentOutput', 'error', %s)
        """,
        (
            request["organization_id"], request["workspace_id"], request["requested_by"], request["id"],
            Jsonb({"error": message[:500]}),
        ),
    )


def enqueue_scheduled_syncs(conn, date_from: date, date_to: date) -> int:
    """Enfileira um sync por WORKSPACE que tenha conexão viva.

    Antes varria `clients`. Depois da migração 0087 a conexão pertence ao
    workspace e `client_id` é opcional — a Operação EG tem conexão com
    `client_id` nulo. Uma varredura por cliente simplesmente NÃO ENCONTRARIA a
    mídia da própria agência, e o sintoma seria o pior possível: nada de erro,
    só um painel que nunca atualiza.

    `distinct on (workspace_id)` porque o sync é do workspace inteiro
    (`provider = 'all'`), não de cada conexão; sem isso, um workspace com
    quatro contas geraria quatro runs concorrentes disputando o mesmo lease.
    """
    rows = conn.execute(
        """
        insert into sync_runs (
          source, organization_id, client_id, workspace_id, provider, status, summary, date_from, date_to
        )
        select
          'performance', pc.organization_id, pc.client_id, pc.workspace_id, 'all', 'queued',
          jsonb_build_object('mode', 'scheduled', 'external_sync', 'queued'),
          %s, %s
        from (
          select distinct on (workspace_id)
                 workspace_id, organization_id, client_id
          from performance_connections
          where status in ('active', 'error')
          order by workspace_id, created_at
        ) pc
        where not exists (
          select 1 from sync_runs sr
          where sr.workspace_id = pc.workspace_id
            and sr.source = 'performance'
            and sr.status in ('queued', 'running')
        )
        returning id
        """,
        (date_from, date_to),
    ).fetchall()
    return len(rows)


def resolve_workspace_id(conn, client_id: UUID) -> UUID:
    """workspace_meta_ads_daily_metrics/workspace_linkedin_ads_daily_metrics são
    chaveadas por workspace_id, diferente das tabelas Google (client_id direto)."""
    row = conn.execute(
        """
        select w.id
        from workspaces w
        join clients c on c.organization_id = w.subject_organization_id
        where c.id = %s
        """,
        (client_id,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"Workspace não encontrado para o client_id {client_id}.")
    return row["id"]


def list_connections(conn, workspace_id: UUID, provider: str):
    """Conexões do WORKSPACE (0087). Chavear por cliente aqui deixaria a
    Operação EG — que não tem registro comercial — sem nenhuma conexão."""
    if provider == "all":
        return conn.execute(
            """
            select id, provider, external_account_id, external_parent_id,
                   credentials_ref, metadata
            from performance_connections
            where workspace_id = %s and status in ('active', 'error')
            order by provider asc
            """,
            (workspace_id,),
        ).fetchall()
    return conn.execute(
        """
        select id, provider, external_account_id, external_parent_id,
               credentials_ref, metadata
        from performance_connections
        where workspace_id = %s and provider = %s and status in ('active', 'error')
        order by created_at asc
        """,
        (workspace_id, provider),
    ).fetchall()


def complete_sync(
    conn,
    sync_id: UUID,
    status: str,
    summary: dict[str, Any],
    records_processed: int,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """
        update sync_runs
        set status = %s,
            summary = %s,
            records_processed = %s,
            error_code = %s,
            error_message = %s,
            finished_at = now()
        where id = %s
        """,
        (status, Jsonb(summary), records_processed, error_code, error_message, sync_id),
    )


def mark_connection_success(conn, connection_id: UUID) -> None:
    conn.execute(
        """
        update performance_connections
        set status = 'active', last_synced_at = now(), last_error_at = null,
            last_error_message = null, updated_at = now()
        where id = %s
        """,
        (connection_id,),
    )


def mark_connection_error(conn, connection_id: UUID, message: str) -> None:
    conn.execute(
        """
        update performance_connections
        set status = 'error', last_error_at = now(), last_error_message = %s,
            updated_at = now()
        where id = %s
        """,
        (message[:2000], connection_id),
    )


def upsert_rows(
    conn,
    table: str,
    columns: tuple[str, ...],
    conflict_columns: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> int:
    if not rows:
        return 0

    update_columns = tuple(column for column in columns if column not in conflict_columns)
    assignments = [
        sql.SQL("{} = excluded.{}").format(sql.Identifier(column), sql.Identifier(column))
        for column in update_columns
    ]
    assignments.append(sql.SQL("updated_at = now()"))
    query = sql.SQL(
        "insert into {} ({}) values ({}) on conflict ({}) do update set {}"
    ).format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        sql.SQL(", ").join(map(sql.Identifier, conflict_columns)),
        sql.SQL(", ").join(assignments),
    )
    # psycopg3: executemany só existe em Cursor, não em Connection (diferente
    # de conn.execute(), que é um atalho — este não tem equivalente).
    with conn.cursor() as cur:
        cur.executemany(query, [tuple(row.get(column) for column in columns) for row in rows])
    return len(rows)


def save_gtm_snapshot(
    conn,
    client_id: UUID,
    account_id: str,
    container_id: str,
    live_version: dict[str, Any],
    findings: list[dict[str, Any]],
) -> int:
    tags = live_version.get("tag", [])
    triggers = live_version.get("trigger", [])
    variables = live_version.get("variable", [])
    snapshot_id = conn.execute(
        """
        insert into gtm_audit_snapshots (
          client_id, account_id, container_id, published_version,
          tags, triggers, variables, metadata
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            client_id,
            account_id,
            container_id,
            live_version.get("containerVersionId") or live_version.get("name") or "live",
            Jsonb(tags),
            Jsonb(triggers),
            Jsonb(variables),
            Jsonb(
                {
                    "container_path": live_version.get("path"),
                    "fingerprint": live_version.get("fingerprint"),
                }
            ),
        ),
    ).fetchone()["id"]

    conn.execute(
        """
        update tracking_findings
        set status = 'resolved', resolved_at = now()
        where client_id = %s and status = 'open'
        """,
        (client_id,),
    )
    for finding in findings:
        conn.execute(
            """
            insert into tracking_findings (
              client_id, snapshot_id, code, title, description, severity, status, metadata
            )
            values (%s, %s, %s, %s, %s, %s, 'open', %s)
            """,
            (
                client_id,
                snapshot_id,
                finding["code"],
                finding["title"],
                finding["description"],
                finding["severity"],
                Jsonb(finding.get("metadata", {})),
            ),
        )
    return len(tags) + len(triggers) + len(variables) + len(findings)
