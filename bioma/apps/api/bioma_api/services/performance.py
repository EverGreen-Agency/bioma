from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import resolve_accessible_client
from bioma_api.db import connect
from bioma_api.repositories import performance as performance_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.performance import (
    AdsAccountSummary,
    AdsCampaignSummary,
    Ga4AcquisitionSummary,
    GscQuerySummary,
    GtmSnapshotSummary,
    PerformanceConnectionCreateRequest,
    PerformanceConnectionSummary,
    PerformanceConnectionUpdateRequest,
    PerformanceInsightSummary,
    PerformanceOverviewResponse,
    PerformanceSyncRunEntry,
    PerformanceSyncRequest,
    PerformanceSyncRunSummary,
    SourceFreshnessSummary,
    TrackingFindingSummary,
)


def list_connections(client_id: UUID, user: CurrentUserResponse) -> list[PerformanceConnectionSummary]:
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        # Chaveado por workspace desde a 0087: a Operação EG conecta mídia
        # sem precisar de um registro em `clients`.
        rows = performance_repo.list_connections(conn, client["workspace_id"])
    return [PerformanceConnectionSummary(**row) for row in rows]


def create_connection(
    client_id: UUID,
    payload: PerformanceConnectionCreateRequest,
    user: CurrentUserResponse,
) -> list[PerformanceConnectionSummary]:
    connection_data = payload.model_dump()
    if not connection_data["external_account_id"].strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ID externo é obrigatório.")

    with connect() as conn:
        client = _accessible_client(conn, client_id, user, "manage_config")
        performance_repo.create_connection(
            conn, client["workspace_id"], client["id"], client["organization_id"], connection_data
        )

    return list_connections(client_id, user)


def update_connection(
    client_id: UUID,
    connection_id: UUID,
    payload: PerformanceConnectionUpdateRequest,
    user: CurrentUserResponse,
) -> list[PerformanceConnectionSummary]:
    updates = payload.model_dump(exclude_unset=True)
    if "external_account_id" in updates and not updates["external_account_id"].strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ID externo é obrigatório.")

    with connect() as conn:
        client = _accessible_client(conn, client_id, user, "manage_config")
        if not performance_repo.update_connection(conn, client["workspace_id"], connection_id, updates):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexão de performance não encontrada.")

    return list_connections(client_id, user)


def list_sync_runs(client_id: UUID, user: CurrentUserResponse) -> list[PerformanceSyncRunEntry]:
    """Ultimas execucoes de sync deste workspace, com status e erro."""
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        rows = performance_repo.list_recent_sync_runs(conn, client["workspace_id"], client["id"])
    return [
        PerformanceSyncRunEntry(
            id=row["id"],
            provider=row["provider"],
            status=row["status"],
            error_code=row["error_code"],
            # `summary.skipped` guarda o motivo das guardas (ex.: workspace sem
            # cliente), que nao passam por error_message.
            error_message=row["error_message"] or (row["summary"] or {}).get("skipped"),
            records_processed=row["records_processed"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )
        for row in rows
    ]


def get_overview(
    client_id: UUID,
    user: CurrentUserResponse,
    date_from: date | None = None,
    date_to: date | None = None,
) -> PerformanceOverviewResponse:
    period_start, period_end = _period_or_default(date_from, date_to)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        resolved_client_id = client["id"]
        ads_row = performance_repo.get_ads_account_summary(conn, resolved_client_id, period_start, period_end)
        daily_rows = performance_repo.list_ads_daily(conn, resolved_client_id, period_start, period_end)
        freshness = performance_repo.list_freshness(conn, resolved_client_id)
        insights = performance_repo.list_insights(conn, resolved_client_id, period_start, period_end)

    return PerformanceOverviewResponse(
        workspace_id=client["workspace_id"],
        client_id=resolved_client_id,
        period_start=period_start,
        period_end=period_end,
        freshness=[SourceFreshnessSummary(**row) for row in freshness],
        ads=AdsAccountSummary(**_derive_ads_metrics(ads_row)),
        daily=list(daily_rows),
        insights=[PerformanceInsightSummary(**row) for row in insights],
    )


def list_ads_campaigns(
    client_id: UUID,
    user: CurrentUserResponse,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
) -> list[AdsCampaignSummary]:
    period_start, period_end = _period_or_default(date_from, date_to)
    bounded_limit = min(max(limit, 1), 200)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        rows = performance_repo.list_ads_campaigns(conn, client["id"], period_start, period_end, bounded_limit)
    return [AdsCampaignSummary(**_derive_ads_metrics(row)) for row in rows]


def list_ga4_acquisition(
    client_id: UUID,
    user: CurrentUserResponse,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
) -> list[Ga4AcquisitionSummary]:
    period_start, period_end = _period_or_default(date_from, date_to)
    bounded_limit = min(max(limit, 1), 200)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        rows = performance_repo.list_ga4_acquisition(conn, client["id"], period_start, period_end, bounded_limit)
    return [Ga4AcquisitionSummary(**row) for row in rows]


def list_gsc_queries(
    client_id: UUID,
    user: CurrentUserResponse,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
) -> list[GscQuerySummary]:
    period_start, period_end = _period_or_default(date_from, date_to)
    bounded_limit = min(max(limit, 1), 200)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        rows = performance_repo.list_gsc_queries(conn, client["id"], period_start, period_end, bounded_limit)
    return [GscQuerySummary(**row) for row in rows]


def list_gtm_snapshots(
    client_id: UUID,
    user: CurrentUserResponse,
    limit: int = 10,
) -> list[GtmSnapshotSummary]:
    bounded_limit = min(max(limit, 1), 50)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user)
        resolved_client_id = client["id"]
        snapshots = performance_repo.list_gtm_snapshots(conn, resolved_client_id, bounded_limit)
        findings = performance_repo.list_tracking_findings(conn, resolved_client_id, [row["id"] for row in snapshots])

    findings_by_snapshot: dict[UUID, list[TrackingFindingSummary]] = {}
    for row in findings:
        snapshot_id = row.pop("snapshot_id")
        findings_by_snapshot.setdefault(snapshot_id, []).append(TrackingFindingSummary(**row))

    return [
        GtmSnapshotSummary(
            **snapshot,
            findings=findings_by_snapshot.get(snapshot["id"], []),
        )
        for snapshot in snapshots
    ]


def request_sync(
    client_id: UUID,
    payload: PerformanceSyncRequest,
    user: CurrentUserResponse,
) -> PerformanceSyncRunSummary:
    period_start, period_end = _period_or_default(payload.date_from, payload.date_to)
    with connect() as conn:
        client = _accessible_client(conn, client_id, user, "manage_config")
        resolved_client_id = client["id"]
        active_connections = performance_repo.count_active_connections(conn, resolved_client_id, payload.provider)
        if active_connections == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nenhuma conexão ativa para o provedor solicitado.",
            )

        summary = {
            "mode": "manual_request",
            "external_sync": "queued",
            "provider": payload.provider,
            "active_connections": active_connections,
            "note": "Sincronização enfileirada para o worker com credenciais Google do ambiente/cofre.",
            "reason": "Solicitação registrada; o worker processará fora da requisição HTTP.",
        }

        row = performance_repo.record_sync_request(
            conn,
            client["organization_id"],
            resolved_client_id,
            payload.provider,
            summary,
            period_start,
            period_end,
            records_processed=0,
        )

    return PerformanceSyncRunSummary(**row)


def _period_or_default(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    period_end = date_to or date.today()
    period_start = date_from or (period_end - timedelta(days=30))
    if period_start > period_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from não pode ser posterior a date_to.",
        )
    return period_start, period_end


def _derive_ads_metrics(row) -> dict:
    data = dict(row or {})
    impressions = _as_int(data.get("impressions"))
    clicks = _as_int(data.get("clicks"))
    cost_micros = _as_int(data.get("cost_micros"))
    conversions = _as_float(data.get("conversions"))
    conversion_value = _as_float(data.get("conversion_value"))
    cost = cost_micros / 1_000_000 if cost_micros else 0

    data.update(
        {
            "impressions": impressions,
            "clicks": clicks,
            "cost_micros": cost_micros,
            "conversions": conversions,
            "conversion_value": conversion_value,
            "ctr": clicks / impressions if impressions else 0,
            "cpc_micros": cost_micros / clicks if clicks else 0,
            "cpa_micros": cost_micros / conversions if conversions else 0,
            "roas": conversion_value / cost if cost else 0,
        }
    )
    return data


def _as_int(value) -> int:
    if isinstance(value, Decimal):
        return int(value)
    return int(value or 0)


def _as_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def _accessible_client(conn, client_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    # Todo o módulo de Performance fica atrás do gate "analytics" para client_user.
    return resolve_accessible_client(conn, client_id, user, module="analytics", capability=capability)
