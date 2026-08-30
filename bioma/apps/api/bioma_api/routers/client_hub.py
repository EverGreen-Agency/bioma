from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.client_hub import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ArtifactCreateRequest,
    ArtifactUpdateRequest,
    ClientCreateRequest,
    ClientPortalResponse,
    ClientRequestCreate,
    ClientRequestUpdate,
    ClientPurgeRequest,
    ClientSummary,
    ClientUpdateRequest,
    CockpitPortfolioSummary,
    DailyBrief,
    MonthlyTargetRequest,
    PortfolioPerformanceRow,
    DeliverableCreateRequest,
    DeliverableUpdateRequest,
    FinancialRecordCreateRequest,
    FinancialRecordSummary,
    FinancialRecordUpdateRequest,
    GlobalDeliverableSummary,
    LeadCreateRequest,
    LeadSummary,
    LeadUpdateRequest,
    PerformanceMetricCreateRequest,
    PerformanceMetricSummary,
    PerformanceMetricUpdateRequest,
)
from bioma_api.services import client_hub as client_hub_service


router = APIRouter(prefix="/clients", tags=["client-hub"])
workspace_router = APIRouter(prefix="/workspaces", tags=["workspace-client-hub"])
backoffice_router = APIRouter(tags=["client-hub-backoffice"])


@router.get("/deliverables/me", response_model=list[GlobalDeliverableSummary])
def list_my_deliverables(user: CurrentUserResponse = Depends(current_user_from_request)):
    return client_hub_service.list_my_deliverables(user)


@backoffice_router.get("/backoffice/daily-brief", response_model=DailyBrief)
def get_daily_brief(user: CurrentUserResponse = Depends(current_user_from_request)):
    """Resumo diario do cockpit (decisao 3, opcao A).

    Sem push por evento, de proposito: notificacao por evento vira ruido, e
    ruido vira gente que ignora o canal inteiro."""
    return client_hub_service.get_daily_brief(user)


@backoffice_router.get("/backoffice/cockpit-summary", response_model=CockpitPortfolioSummary)
def get_cockpit_summary(user: CurrentUserResponse = Depends(current_user_from_request)):
    return client_hub_service.get_cockpit_summary(user)


@backoffice_router.get("/backoffice/portfolio-performance", response_model=list[PortfolioPerformanceRow])
def get_portfolio_performance(
    days: int = 30,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    """Rollup executivo: midia paga de todos os clientes lado a lado."""
    return client_hub_service.get_portfolio_performance(user, days)


@backoffice_router.put(
    "/backoffice/clients/{client_id}/monthly-target",
    response_model=list[PortfolioPerformanceRow],
)
def set_monthly_target(
    client_id: UUID,
    payload: MonthlyTargetRequest,
    days: int = 30,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    """Meta de leads e verba do mês — fecha o ciclo meta x realizado no rollup."""
    return client_hub_service.set_monthly_target(client_id, payload, user, days)


@router.get("", response_model=list[ClientSummary])
def list_clients(user: CurrentUserResponse = Depends(current_user_from_request)) -> list[ClientSummary]:
    return client_hub_service.list_clients(user)


@router.post("", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.create_client(payload, user)


@router.get("/{client_id}", response_model=ClientPortalResponse)
@workspace_router.get("/{client_id}", response_model=ClientPortalResponse)
def get_client_portal(
    client_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.get_client_portal(client_id, user)


@router.post("/{client_id}/requests", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
@workspace_router.post("/{client_id}/requests", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
def create_client_request(
    client_id: UUID,
    payload: ClientRequestCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.create_client_request(client_id, payload, user)


@router.patch("/{client_id}/requests/{request_id}", response_model=ClientPortalResponse)
@workspace_router.patch("/{client_id}/requests/{request_id}", response_model=ClientPortalResponse)
def update_client_request(
    client_id: UUID,
    request_id: UUID,
    payload: ClientRequestUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.update_client_request(client_id, request_id, payload, user)


@router.patch("/{client_id}", response_model=ClientPortalResponse)
@workspace_router.patch("/{client_id}", response_model=ClientPortalResponse)
def update_client(
    client_id: UUID,
    payload: ClientUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.update_client(client_id, payload, user)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
@workspace_router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> Response:
    client_hub_service.archive_client(client_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{client_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
def purge_client(
    client_id: UUID,
    payload: ClientPurgeRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> Response:
    client_hub_service.purge_client(client_id, payload.confirmation, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{client_id}/artifacts", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
@workspace_router.post("/{client_id}/artifacts", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
def create_artifact(
    client_id: UUID,
    payload: ArtifactCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.create_artifact(client_id, payload, user)


@router.patch("/{client_id}/artifacts/{artifact_id}", response_model=ClientPortalResponse)
@workspace_router.patch("/{client_id}/artifacts/{artifact_id}", response_model=ClientPortalResponse)
def update_artifact(
    client_id: UUID,
    artifact_id: UUID,
    payload: ArtifactUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.update_artifact(client_id, artifact_id, payload, user)


@router.delete("/{client_id}/artifacts/{artifact_id}", response_model=ClientPortalResponse)
@workspace_router.delete("/{client_id}/artifacts/{artifact_id}", response_model=ClientPortalResponse)
def delete_artifact(
    client_id: UUID,
    artifact_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.delete_artifact(client_id, artifact_id, user)


@router.post("/{client_id}/deliverables", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
@workspace_router.post("/{client_id}/deliverables", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
def create_deliverable(
    client_id: UUID,
    payload: DeliverableCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.create_deliverable(client_id, payload, user)


@router.patch("/{client_id}/deliverables/{deliverable_id}", response_model=ClientPortalResponse)
@workspace_router.patch("/{client_id}/deliverables/{deliverable_id}", response_model=ClientPortalResponse)
def update_deliverable(
    client_id: UUID,
    deliverable_id: UUID,
    payload: DeliverableUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.update_deliverable(client_id, deliverable_id, payload, user)


@router.delete("/{client_id}/deliverables/{deliverable_id}", response_model=ClientPortalResponse)
@workspace_router.delete("/{client_id}/deliverables/{deliverable_id}", response_model=ClientPortalResponse)
def delete_deliverable(
    client_id: UUID,
    deliverable_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.delete_deliverable(client_id, deliverable_id, user)


@router.post("/{client_id}/approvals", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
@workspace_router.post("/{client_id}/approvals", response_model=ClientPortalResponse, status_code=status.HTTP_201_CREATED)
def create_approval(
    client_id: UUID,
    payload: ApprovalCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.create_approval(client_id, payload, user)


@router.patch("/{client_id}/approvals/{approval_id}", response_model=ClientPortalResponse)
@workspace_router.patch("/{client_id}/approvals/{approval_id}", response_model=ClientPortalResponse)
def decide_approval(
    client_id: UUID,
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ClientPortalResponse:
    return client_hub_service.decide_approval(client_id, approval_id, payload, user)


@router.get("/{client_id}/leads", response_model=list[LeadSummary])
@workspace_router.get("/{client_id}/leads", response_model=list[LeadSummary])
def list_leads(
    client_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[LeadSummary]:
    return client_hub_service.list_leads(client_id, user)


@router.post("/{client_id}/leads", response_model=list[LeadSummary], status_code=status.HTTP_201_CREATED)
@workspace_router.post("/{client_id}/leads", response_model=list[LeadSummary], status_code=status.HTTP_201_CREATED)
def create_lead(
    client_id: UUID,
    payload: LeadCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[LeadSummary]:
    return client_hub_service.create_lead(client_id, payload, user)


@router.patch("/{client_id}/leads/{lead_id}", response_model=list[LeadSummary])
@workspace_router.patch("/{client_id}/leads/{lead_id}", response_model=list[LeadSummary])
def update_lead(
    client_id: UUID,
    lead_id: UUID,
    payload: LeadUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[LeadSummary]:
    return client_hub_service.update_lead(client_id, lead_id, payload, user)


@router.delete("/{client_id}/leads/{lead_id}", response_model=list[LeadSummary])
@workspace_router.delete("/{client_id}/leads/{lead_id}", response_model=list[LeadSummary])
def delete_lead(
    client_id: UUID,
    lead_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[LeadSummary]:
    return client_hub_service.delete_lead(client_id, lead_id, user)


@router.get("/{client_id}/finance", response_model=list[FinancialRecordSummary])
@workspace_router.get("/{client_id}/finance", response_model=list[FinancialRecordSummary])
def list_financial_records(
    client_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[FinancialRecordSummary]:
    return client_hub_service.list_financial_records(client_id, user)


@router.post("/{client_id}/finance", response_model=list[FinancialRecordSummary], status_code=status.HTTP_201_CREATED)
@workspace_router.post("/{client_id}/finance", response_model=list[FinancialRecordSummary], status_code=status.HTTP_201_CREATED)
def create_financial_record(
    client_id: UUID,
    payload: FinancialRecordCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[FinancialRecordSummary]:
    return client_hub_service.create_financial_record(client_id, payload, user)


@router.patch("/{client_id}/finance/{record_id}", response_model=list[FinancialRecordSummary])
@workspace_router.patch("/{client_id}/finance/{record_id}", response_model=list[FinancialRecordSummary])
def update_financial_record(
    client_id: UUID,
    record_id: UUID,
    payload: FinancialRecordUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[FinancialRecordSummary]:
    return client_hub_service.update_financial_record(client_id, record_id, payload, user)


@router.delete("/{client_id}/finance/{record_id}", response_model=list[FinancialRecordSummary])
@workspace_router.delete("/{client_id}/finance/{record_id}", response_model=list[FinancialRecordSummary])
def delete_financial_record(
    client_id: UUID,
    record_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[FinancialRecordSummary]:
    return client_hub_service.delete_financial_record(client_id, record_id, user)


@router.get("/{client_id}/metrics", response_model=list[PerformanceMetricSummary])
@workspace_router.get("/{client_id}/metrics", response_model=list[PerformanceMetricSummary])
def list_performance_metrics(
    client_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[PerformanceMetricSummary]:
    return client_hub_service.list_performance_metrics(client_id, user)


@router.post("/{client_id}/metrics", response_model=list[PerformanceMetricSummary], status_code=status.HTTP_201_CREATED)
@workspace_router.post("/{client_id}/metrics", response_model=list[PerformanceMetricSummary], status_code=status.HTTP_201_CREATED)
def create_performance_metric(
    client_id: UUID,
    payload: PerformanceMetricCreateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[PerformanceMetricSummary]:
    return client_hub_service.create_performance_metric(client_id, payload, user)


@router.patch("/{client_id}/metrics/{metric_id}", response_model=list[PerformanceMetricSummary])
@workspace_router.patch("/{client_id}/metrics/{metric_id}", response_model=list[PerformanceMetricSummary])
def update_performance_metric(
    client_id: UUID,
    metric_id: UUID,
    payload: PerformanceMetricUpdateRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[PerformanceMetricSummary]:
    return client_hub_service.update_performance_metric(client_id, metric_id, payload, user)


@router.delete("/{client_id}/metrics/{metric_id}", response_model=list[PerformanceMetricSummary])
@workspace_router.delete("/{client_id}/metrics/{metric_id}", response_model=list[PerformanceMetricSummary])
def delete_performance_metric(
    client_id: UUID,
    metric_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[PerformanceMetricSummary]:
    return client_hub_service.delete_performance_metric(client_id, metric_id, user)
