"""Leitura das conversas e da trilha de auditoria do copiloto.

Escopo (decisão do Eduardo: copiloto é EG-only): toda entrada exige
`require_platform_admin`. Dentro da EG, cada um lê a própria conversa; a
auditoria de execução é aberta a qualquer admin — o ponto dela é justamente
poder conferir o trabalho do agente sem depender de quem o acionou.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import ai_routing as routing_repo
from bioma_api.repositories import copilot_traces as repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.copilot import (
    CopilotDailyUsage,
    CopilotBlock,
    CopilotProviderUsage,
    CopilotQuotaBucket,
    CopilotRoutedAccountQuota,
    CopilotRunStep,
    CopilotRunTrace,
    CopilotThreadSummary,
    CopilotUsageSummary,
)


def list_threads(status_val: str, user: CurrentUserResponse) -> list[CopilotThreadSummary]:
    require_platform_admin(user)
    with connect() as conn:
        rows = repo.list_threads(conn, user.id, status_val)
    return [CopilotThreadSummary(**row) for row in rows]


def get_thread_runs(thread_id: UUID, user: CurrentUserResponse) -> list[CopilotRunTrace]:
    require_platform_admin(user)
    with connect() as conn:
        thread = repo.get_thread(conn, thread_id)
        if not thread or thread["user_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
        runs = repo.list_runs(conn, thread_id)
        return [_trace(conn, run, repo.list_steps(conn, run["id"])) for run in runs]


def archive_thread(thread_id: UUID, user: CurrentUserResponse) -> CopilotThreadSummary:
    require_platform_admin(user)
    with connect() as conn:
        thread = repo.get_thread(conn, thread_id)
        if not thread or thread["user_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
        repo.archive_thread(conn, thread_id)
        # Relê pela listagem para devolver com run_count/last_message preenchidos.
        row = next(
            (item for item in repo.list_threads(conn, user.id, "archived") if item["id"] == thread_id),
            None,
        )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    return CopilotThreadSummary(**row)


def get_run(run_id: UUID, user: CurrentUserResponse) -> CopilotRunTrace:
    require_platform_admin(user)
    with connect() as conn:
        run = repo.get_run(conn, run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada.")
        steps = repo.list_steps(conn, run_id)
        return _trace(conn, run, steps)


def usage(days: int, mine_only: bool, user: CurrentUserResponse) -> CopilotUsageSummary:
    require_platform_admin(user)
    scoped_user = user.id if mine_only else None
    with connect() as conn:
        row = repo.usage_summary(conn, scoped_user, days)
        routed = repo.list_routed_accounts_in_window(conn, scoped_user, days)
        routed_accounts = [
            account for account in (_routed_account_quota(conn, item["account_id"]) for item in routed) if account
        ]
        daily = repo.daily_usage(conn, scoped_user, days)
        by_provider = repo.usage_by_provider(conn, scoped_user, days)
    return CopilotUsageSummary(
        **{key: int(value) for key, value in row.items()},
        routed_accounts=routed_accounts,
        daily=[CopilotDailyUsage(**item) for item in daily],
        by_provider=[CopilotProviderUsage(**item) for item in by_provider],
    )


def _routed_account_quota(conn, account_id) -> CopilotRoutedAccountQuota | None:
    """Cota ATUAL da conta — não uma foto de quando a execução rodou.

    Lida na hora porque cota é estado presente: o que sobrava na terça não diz
    nada sobre o que sobra hoje.
    """
    account = routing_repo.get_account(conn, account_id)
    if not account:
        # Conta apagada depois de ter atendido execuções passadas — a trilha
        # daquelas execuções continua válida, só não dá pra mostrar cota atual
        # de algo que não existe mais.
        return None
    buckets = routing_repo.latest_quota_for_account(conn, account_id)
    return CopilotRoutedAccountQuota(
        account_id=account["id"],
        display_name=account["display_name"],
        channel=account["channel"],
        buckets=[
            CopilotQuotaBucket(**{key: bucket[key] for key in (
                "bucket_key", "scope", "model_id", "remaining_percent", "unit",
                "resets_at", "source", "confidence", "measured_at",
            )})
            for bucket in buckets
        ],
    )


def _trace(conn, run: dict, steps: list[dict]) -> CopilotRunTrace:
    routed_account = _routed_account_quota(conn, run["routed_account_id"]) if run.get("routed_account_id") else None
    return CopilotRunTrace(
        **{key: run[key] for key in (
            "id", "thread_id", "message", "answer", "status", "error_message",
            "generation_mode", "provider", "model", "confidence",
            "dossier_summary", "memories_used", "skills_used", "sources", "actions", "attachments",
            "input_tokens", "output_tokens", "cost_cents", "duration_ms", "created_at",
        )},
        response_blocks=[CopilotBlock(**item) for item in (run.get("response_blocks") or [])],
        steps=[CopilotRunStep(**{key: step[key] for key in (
            "position", "kind", "label", "status", "detail", "payload", "duration_ms",
        )}) for step in steps],
        routed_account=routed_account,
    )
