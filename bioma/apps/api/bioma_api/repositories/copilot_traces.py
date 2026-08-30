"""Persistência da conversa com o copiloto e da trilha de cada execução.

A trilha existe para responder, depois do fato: o que ele leu, o que decidiu, o
que executou de verdade, quanto custou e quanto demorou. Sem isso, "o copiloto
disse que criou as subtarefas" e "o copiloto criou as subtarefas" são a mesma
frase na tela.
"""

from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def create_thread(
    conn,
    user_id: UUID,
    surface: str,
    workspace_id: UUID | None,
    task_id: UUID | None,
    title: str | None,
) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            insert into copilot_threads (user_id, surface, workspace_id, task_id, title)
            values (%s, %s, %s, %s, %s)
            returning *
            """,
            (user_id, surface, workspace_id, task_id, (title or "")[:200] or None),
        )
        return dict(cur.fetchone())


def get_thread(conn, thread_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select * from copilot_threads where id = %s", (thread_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_threads(conn, user_id: UUID, status_val: str = "active", limit: int = 50) -> list[dict[str, Any]]:
    """Threads do próprio usuário, com o resumo que a lista lateral precisa.

    Escopo por `user_id` de propósito: a conversa é do interlocutor. Ver a
    conversa de outra pessoa é auditoria, e passa pela tela de auditoria.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select t.*,
                   coalesce(r.run_count, 0) as run_count,
                   r.last_message
            from copilot_threads t
            left join lateral (
              select count(*) as run_count,
                     (array_agg(message order by created_at desc))[1] as last_message
              from copilot_runs where thread_id = t.id
            ) r on true
            where t.user_id = %s and t.status = %s
            order by t.last_message_at desc
            limit %s
            """,
            (user_id, status_val, limit),
        )
        return list(cur.fetchall())


def archive_thread(conn, thread_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "update copilot_threads set status = 'archived' where id = %s returning *", (thread_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def touch_thread(conn, thread_id: UUID, title_if_empty: str | None = None) -> None:
    """Sobe a thread na lista e batiza no primeiro turno.

    O título vem da primeira mensagem porque é o que a pessoa reconhece — pedir
    para nomear a conversa antes de tê-la é atrito puro.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            update copilot_threads
            set last_message_at = now(),
                title = coalesce(title, %s)
            where id = %s
            """,
            ((title_if_empty or "")[:200] or None, thread_id),
        )


def start_run(conn, data: dict[str, Any]) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            insert into copilot_runs (thread_id, user_id, surface, workspace_id, task_id, message)
            values (%s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                data["thread_id"],
                data["user_id"],
                data["surface"],
                data.get("workspace_id"),
                data.get("task_id"),
                data["message"],
            ),
        )
        return dict(cur.fetchone())


def finish_run(conn, run_id: UUID, data: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            update copilot_runs set
              answer = %s, confidence = %s, generation_mode = %s, provider = %s, model = %s,
              status = %s, error_message = %s,
              dossier_summary = %s, memories_used = %s, skills_used = %s, sources = %s, actions = %s,
              response_blocks = %s,
              attachments = %s,
              input_tokens = %s, output_tokens = %s, cost_cents = %s, duration_ms = %s,
              routed_account_id = %s
            where id = %s
            """,
            (
                data.get("answer"),
                data.get("confidence"),
                data.get("generation_mode"),
                data.get("provider"),
                data.get("model"),
                data.get("status", "completed"),
                data.get("error_message"),
                Jsonb(data.get("dossier_summary") or {}),
                Jsonb(data.get("memories_used") or []),
                Jsonb(data.get("skills_used") or []),
                Jsonb(data.get("sources") or []),
                Jsonb(data.get("actions") or []),
                Jsonb(data.get("response_blocks") or []),
                Jsonb(data.get("attachments") or []),
                data.get("input_tokens"),
                data.get("output_tokens"),
                data.get("cost_cents"),
                data.get("duration_ms"),
                data.get("routed_account_id"),
                run_id,
            ),
        )


def bind_thread_entities(
    conn, thread_id: UUID, user_id: UUID, entities: list[tuple[str, UUID]]
) -> None:
    for entity_type, entity_id in entities:
        conn.execute(
            """
            insert into copilot_thread_entities (
              thread_id, entity_type, entity_id, relationship, created_by
            ) values (%s, %s, %s, 'context', %s)
            on conflict do nothing
            """,
            (thread_id, entity_type, entity_id, user_id),
        )


def add_step(conn, run_id: UUID, position: int, step: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into copilot_run_steps (run_id, position, kind, label, status, detail, payload, duration_ms)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id,
                position,
                step["kind"],
                step["label"][:300],
                step["status"],
                (step.get("detail") or "")[:2000] or None,
                Jsonb(step.get("payload") or {}),
                step.get("duration_ms"),
            ),
        )


def list_runs(conn, thread_id: UUID) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select * from copilot_runs where thread_id = %s order by created_at", (thread_id,))
        return list(cur.fetchall())


def get_run(conn, run_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select * from copilot_runs where id = %s", (run_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_steps(conn, run_id: UUID) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select * from copilot_run_steps where run_id = %s order by position", (run_id,))
        return list(cur.fetchall())


def usage_summary(conn, user_id: UUID | None = None, days: int = 30) -> dict[str, Any]:
    """Quanto o copiloto consumiu na janela — token, custo, cota e tempo.

    `cost_cents` soma só o que tem preço em dinheiro real (chave de API, ou o
    que a própria CLI de assinatura reportou). `runs_without_cost` conta só o
    gap de verdade: execução por CHAVE DE API cujo modelo não está na tabela de
    preços. Execução roteada por assinatura (`routed_account_id` preenchido)
    sem custo em dinheiro não é um gap — é o esperado, porque assinatura não é
    cobrada por token. `routed_runs` conta essas à parte.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
              count(*) as runs,
              count(*) filter (where status = 'failed') as failed_runs,
              count(*) filter (where generation_mode = 'preview') as preview_runs,
              count(*) filter (where routed_account_id is not null) as routed_runs,
              count(*) filter (
                where cost_cents is null and generation_mode = 'live' and routed_account_id is null
              ) as runs_without_cost,
              coalesce(sum(input_tokens), 0) as input_tokens,
              coalesce(sum(output_tokens), 0) as output_tokens,
              coalesce(sum(cost_cents), 0) as cost_cents,
              coalesce(round(avg(duration_ms)), 0) as avg_duration_ms
            from copilot_runs
            where created_at >= now() - make_interval(days => %s)
              and (%s::uuid is null or user_id = %s::uuid)
            """,
            (days, user_id, user_id),
        )
        return dict(cur.fetchone())


def daily_usage(conn, user_id: UUID | None, days: int) -> list[dict[str, Any]]:
    """Série diária para os gráficos de tendência do copiloto.

    Sem zero-fill: dia sem execução simplesmente não aparece na série, mesmo
    padrão das outras séries diárias do Bioma (`list_ads_daily`).
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
              date_trunc('day', created_at)::date as day,
              count(*) as runs,
              count(*) filter (where routed_account_id is not null) as routed_runs,
              count(*) filter (where status = 'failed') as failed_runs,
              coalesce(sum(cost_cents), 0) as cost_cents,
              coalesce(sum(input_tokens), 0) as input_tokens,
              coalesce(sum(output_tokens), 0) as output_tokens
            from copilot_runs
            where created_at >= now() - make_interval(days => %s)
              and (%s::uuid is null or user_id = %s::uuid)
            group by 1
            order by 1
            """,
            (days, user_id, user_id),
        )
        return list(cur.fetchall())


def usage_by_provider(conn, user_id: UUID | None, days: int) -> list[dict[str, Any]]:
    """Quebra por provedor+modelo na janela — de onde vieram as respostas."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
              coalesce(provider, 'desconhecido') as provider,
              coalesce(model, 'desconhecido') as model,
              count(*) as runs,
              count(*) filter (where routed_account_id is not null) as routed_runs,
              coalesce(sum(cost_cents), 0) as cost_cents
            from copilot_runs
            where created_at >= now() - make_interval(days => %s)
              and (%s::uuid is null or user_id = %s::uuid)
            group by provider, model
            order by runs desc
            """,
            (days, user_id, user_id),
        )
        return list(cur.fetchall())


def list_routed_accounts_in_window(conn, user_id: UUID | None, days: int) -> list[dict[str, Any]]:
    """Contas de assinatura que atenderam o copiloto na janela, com quantas vezes.

    A cota em si (quanto sobra, quando reseta) não vem daqui — vem de
    `ai_quota_buckets`, lida na hora, porque cota é o estado ATUAL da conta, não
    algo que faça sentido guardar por execução passada.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select routed_account_id as account_id, count(*) as run_count, max(created_at) as last_used_at
            from copilot_runs
            where routed_account_id is not null
              and created_at >= now() - make_interval(days => %s)
              and (%s::uuid is null or user_id = %s::uuid)
            group by routed_account_id
            order by run_count desc
            """,
            (days, user_id, user_id),
        )
        return list(cur.fetchall())
