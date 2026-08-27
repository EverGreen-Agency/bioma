from datetime import date, timedelta
from typing import Any

from bioma_worker.config import get_settings
from bioma_worker.db import connect
from bioma_worker.ai_content import generate_content
from bioma_worker.ai_providers import execute_candidate
from bioma_worker.ai_routing import rank_candidates
from bioma_worker.quota_collectors import (
    collect_antigravity_usage,
    collect_claude_rate_limits,
    collect_codex_rate_limits,
)
from bioma_worker import storage


def reclaim_stalled_jobs() -> dict[str, int]:
    """Passe do reaper (QUEUE-001), executado antes de consumir a fila.

    O worker é um processo em lote, não um daemon: rodar aqui garante que todo
    ciclo comece recuperando o que ficou preso, sem exigir agendamento próprio.
    """
    settings = get_settings()
    with connect() as conn:
        return storage.reclaim_stalled_jobs(
            conn,
            settings.job_lease_seconds,
            settings.job_max_attempts,
        )


def run_next_job() -> dict[str, Any] | None:
    with connect() as conn:
        job_type = storage.next_job_type(conn)
    if job_type == "ai_content":
        return run_next_ai_content()
    if job_type == "performance":
        return run_next_sync()
    if job_type == "ai_workflow":
        return run_next_ai_workflow()
    if job_type == "ai_quota":
        return run_next_ai_quota_collection()
    return None


def run_next_ai_content() -> dict[str, Any] | None:
    with connect() as conn:
        request = storage.claim_next_ai_content(conn)
    if not request:
        return None

    try:
        result = generate_content(request, get_settings())
        with connect() as conn:
            storage.complete_ai_content(conn, request, result)
        return {
            "job": "ai_content",
            "id": str(request["id"]),
            "status": "ready",
            "provider": result["provider"],
            "generation_mode": result["generation_mode"],
        }
    except Exception as exc:  # noqa: BLE001 - job failure must be persisted
        message = _safe_error(exc)
        with connect() as conn:
            storage.fail_ai_content(conn, request, message)
        return {"job": "ai_content", "id": str(request["id"]), "status": "error", "error": message}


def run_next_ai_workflow() -> dict[str, Any] | None:
    with connect() as conn:
        job = storage.claim_next_ai_workflow(conn)
    if not job:
        return None
    with connect() as conn:
        candidates = rank_candidates(job, storage.list_ai_route_candidates(conn, job))
    eligible = [candidate for candidate in candidates if candidate["eligible"]]
    if not eligible:
        message = "Nenhum provider/modelo elegível. Configure conta, catálogo, política e cota no control plane."
        with connect() as conn:
            storage.fail_ai_workflow_step(conn, job, message)
        return {
            "job": "ai_workflow",
            "id": str(job["run_id"]),
            "step": job["step_key"],
            "status": "failed",
            "error": message,
        }

    failures: list[str] = []
    for candidate in eligible:
        with connect() as conn:
            attempt = storage.start_ai_execution_attempt(conn, job, candidate)
        try:
            result = execute_candidate(candidate, job, get_settings())
            with connect() as conn:
                storage.complete_ai_workflow_step(conn, job, candidate, attempt["id"], result)
            return {
                "job": "ai_workflow",
                "id": str(job["run_id"]),
                "step": job["step_key"],
                "status": "waiting_approval" if job["interactive"] else "completed",
                "provider": candidate["provider"],
                "channel": candidate["channel"],
                "model": candidate["model_id"],
                "attempt": attempt["attempt_number"],
            }
        except Exception as exc:  # noqa: BLE001 - fallback must persist each provider failure
            message = _safe_error(exc)
            failures.append(f"{candidate['channel']}/{candidate['model_id']}: {message}")
            with connect() as conn:
                storage.fail_ai_execution_attempt(conn, attempt["id"], message)
            if candidate.get("allow_fallback") is False:
                break

    final_message = "Todos os candidatos elegíveis falharam: " + " | ".join(failures)
    with connect() as conn:
        storage.fail_ai_workflow_step(conn, job, final_message)
    return {
        "job": "ai_workflow",
        "id": str(job["run_id"]),
        "step": job["step_key"],
        "status": "failed",
        "error": final_message[:2000],
    }


def run_next_ai_quota_collection() -> dict[str, Any] | None:
    with connect() as conn:
        job = storage.claim_next_ai_quota_collection(conn)
    if not job:
        return None
    try:
        settings = get_settings()
        from bioma_worker.provider_credentials import provider_process_environment

        with provider_process_environment(job, settings) as process_env:
            binary = (job.get("settings") or {}).get("binary_path")
            if job["collector"] == "codex_app_server":
                buckets = collect_codex_rate_limits(binary or settings.codex_cli_path, env=process_env)
            elif job["collector"] == "claude_statusline":
                buckets = collect_claude_rate_limits(binary or settings.claude_cli_path, env=process_env)
            elif job["collector"] == "antigravity_usage":
                buckets = collect_antigravity_usage(binary or settings.antigravity_cli_path, env=process_env)
            else:
                raise RuntimeError(f"Coletor não suportado: {job['collector']}")
        with connect() as conn:
            storage.complete_ai_quota_collection(conn, job, buckets)
        return {
            "job": "ai_quota",
            "id": str(job["id"]),
            "account_id": str(job["account_id"]),
            "status": "completed",
            "buckets_recorded": len(buckets),
        }
    except Exception as exc:  # noqa: BLE001 - probe failure must be visible in control plane
        message = _safe_error(exc)
        with connect() as conn:
            storage.fail_ai_quota_collection(conn, job, message)
        return {
            "job": "ai_quota",
            "id": str(job["id"]),
            "account_id": str(job["account_id"]),
            "status": "failed",
            "error": message,
        }


def run_next_sync() -> dict[str, Any] | None:
    from bioma_worker.google_client import GoogleApiClient
    import httpx
    with connect() as conn:
        sync_run = storage.claim_next_sync(conn)
    if not sync_run:
        return None


    # LIMITE CONHECIDO, declarado em vez de descoberto em producao.
    #
    # A conexao ja pertence ao workspace (0087), mas o caminho de ESCRITA nao:
    # os 16 provedores montam linhas com `client_id`, e as tabelas diarias do
    # Google exigem `workspace_id NOT NULL` preenchido por um trigger que
    # resolve workspace A PARTIR do cliente. Com `client_id` nulo — que e o
    # caso da Operacao EG — o trigger desiste e o insert morre com um erro cru
    # de constraint no meio da rodada, depois de ja ter chamado a API externa.
    #
    # Recusar aqui troca esse erro incompreensivel por um motivo legivel na
    # trilha do sync. Nao conserta o caminho de escrita; torna a falha
    # diagnosticavel e deixa registrado o que falta fazer.
    if not sync_run.get("client_id"):
        reason = (
            "Sync de performance ainda exige um registro de cliente. A escrita das "
            "tabelas diarias e chaveada por client_id (16 provedores + trigger de "
            "workspace), e migra-la e um trabalho separado. Workspace sem cliente "
            "— como a Operacao EG — nao sincroniza ainda."
        )
        with connect() as conn:
            storage.complete_sync(
                conn,
                sync_run["id"],
                "error",
                {"skipped": reason},
                0,
                error_code="WORKSPACE_WITHOUT_CLIENT",
                error_message=reason,
            )
        return {
            "job": "performance",
            "id": str(sync_run["id"]),
            "status": "error",
            "reason": reason,
        }

    settings = get_settings()
    google_client = GoogleApiClient(settings)
    date_to = sync_run["date_to"] or date.today()
    date_from = sync_run["date_from"] or (date_to - timedelta(days=30))

    with connect() as conn:
        # Por workspace (0087): a Operação EG tem conexão sem `client_id`, e
        # listar por cliente a deixaria de fora sem gerar erro nenhum.
        #
        # O fallback existe para linhas LEGADAS: `sync_runs` criados antes da
        # 0087 têm `workspace_id` nulo, e listar por nulo devolveria zero
        # conexões — o sync "terminaria com sucesso" sem sincronizar nada, que
        # é o pior desfecho possível. Resolver pelo cliente mantém essas linhas
        # funcionando em vez de falharem caladas.
        workspace_id = sync_run.get("workspace_id")
        if not workspace_id and sync_run.get("client_id"):
            workspace_id = storage.resolve_workspace_id(conn, sync_run["client_id"])
        connections = storage.list_connections(conn, workspace_id, sync_run["provider"] or "all")

    results: dict[str, dict[str, Any]] = {}
    total_records = 0

    with httpx.Client(timeout=settings.google_request_timeout_seconds) as generic_client:
        for connection in connections:
            provider = connection["provider"]
            result_key = f"{provider}:{connection['external_account_id']}"
            # Renova o lease a cada provider: sem isto, um sync longo seria
            # reenfileirado pelo reaper enquanto ainda está rodando.
            with connect() as conn:
                storage.heartbeat_sync(conn, sync_run["id"])
            try:
                _validate_credentials_reference(connection)
                with connect() as conn:
                    records = _sync_provider(
                        conn,
                        google_client,
                        generic_client,
                        settings,
                        sync_run["client_id"],
                        connection,
                        date_from,
                        date_to,
                    )
                    storage.mark_connection_success(conn, connection["id"])
                results[result_key] = {"provider": provider, "status": "ok", "records": records}
                total_records += records
            except Exception as exc:  # noqa: BLE001 - provider failures must be isolated
                message = _safe_error(exc)
                with connect() as conn:
                    storage.mark_connection_error(conn, connection["id"], message)
                results[result_key] = {
                    "provider": provider,
                    "status": "error",
                    "records": 0,
                    "error": message,
                }

    success_count = sum(1 for result in results.values() if result["status"] == "ok")
    error_count = sum(1 for result in results.values() if result["status"] == "error")
    if success_count and error_count:
        final_status = "partial"
    elif success_count:
        final_status = "ok"
    else:
        final_status = "error"

    summary = {
        "mode": "worker",
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "providers": results,
    }
    error_message = None
    if not connections:
        error_message = "Nenhuma conexão ativa encontrada para a sincronização."
        summary["error"] = error_message
    elif final_status == "error":
        error_message = "Todos os providers falharam; consulte o resumo por provider."

    with connect() as conn:
        storage.complete_sync(
            conn,
            sync_run["id"],
            final_status,
            summary,
            total_records,
            error_code="PROVIDER_SYNC_FAILED" if final_status == "error" else None,
            error_message=error_message,
        )
    return {"id": str(sync_run["id"]), "status": final_status, **summary}


def _sync_provider(
    conn,
    google_client,
    generic_client,
    settings,
    client_id,
    connection,
    date_from: date,
    date_to: date,
) -> int:
    from bioma_worker.providers import (
        adsense, ga4, google_ads, google_business_profile, gtm, hubspot, instagram_organic,
        linkedin_ads, linkedin_organic, meta_ads, openai_ads, rd_station_crm, search_console, tiktok_ads,
        tiktok_organic, youtube_organic,
    )
    provider = connection["provider"]
    if provider == "openai_ads":
        return openai_ads.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "google_ads":
        return google_ads.sync(conn, google_client, settings, client_id, connection, date_from, date_to)
    if provider == "ga4":
        return ga4.sync(conn, google_client, client_id, connection, date_from, date_to)
    if provider == "search_console":
        return search_console.sync(conn, google_client, client_id, connection, date_from, date_to)
    if provider == "gtm":
        return gtm.sync(conn, google_client, client_id, connection)
    if provider == "meta_ads":
        return meta_ads.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "linkedin_ads":
        return linkedin_ads.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "instagram_organic":
        return instagram_organic.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "google_business_profile":
        return google_business_profile.sync(conn, google_client, client_id, connection, date_from, date_to)
    if provider == "google_adsense":
        return adsense.sync(conn, google_client, client_id, connection, date_from, date_to)
    if provider == "youtube_organic":
        return youtube_organic.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "tiktok_organic":
        return tiktok_organic.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "tiktok_ads":
        return tiktok_ads.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "linkedin_organic":
        return linkedin_organic.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "rd_station_crm":
        return rd_station_crm.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    if provider == "hubspot":
        return hubspot.sync(conn, generic_client, settings, client_id, connection, date_from, date_to)
    raise RuntimeError(f"Provider não suportado: {provider}")


_SUPPORTED_CREDENTIALS_REFS = (
    "env:GOOGLE_SERVICE_ACCOUNT_JSON",
    "env:META_ADS_ACCESS_TOKEN",
    "env:LINKEDIN_ADS_ACCESS_TOKEN",
    "env:INSTAGRAM_ACCESS_TOKEN",
    "env:YOUTUBE_API_KEY",
    "env:OPENAI_ADS_API_KEY",
)


def _validate_credentials_reference(connection: dict[str, Any]) -> None:
    reference = connection.get("credentials_ref")
    if reference and reference not in _SUPPORTED_CREDENTIALS_REFS:
        raise RuntimeError(
            f"credentials_ref não suportado neste ambiente; use um de {_SUPPORTED_CREDENTIALS_REFS} ou integre um cofre."
        )


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:2000]
