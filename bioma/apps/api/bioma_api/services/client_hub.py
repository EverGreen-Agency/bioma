from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import (
    CLIENT_MODULES,
    is_platform_admin,
    require_platform_admin,
    resolve_accessible_client,
)
from bioma_api import daily_brief
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.client_hub import (
    DailyBrief,
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ArtifactCreateRequest,
    ArtifactUpdateRequest,
    ClientCreateRequest,
    ClientPortalResponse,
    ClientSummary,
    ClientUpdateRequest,
    CockpitPortfolioSummary,
    MonthlyTargetRequest,
    PortfolioPerformanceRow,
    DeliverableCreateRequest,
    DeliverableUpdateRequest,
    FinancialRecordCreateRequest,
    FinancialRecordSummary,
    FinancialRecordUpdateRequest,
    LeadCreateRequest,
    LeadSummary,
    LeadUpdateRequest,
    PerformanceMetricCreateRequest,
    PerformanceMetricSummary,
    PerformanceMetricUpdateRequest,
)
from bioma_api.services.storage import StorageNotConfiguredError, StorageOperationError, delete_object


def list_clients(user: CurrentUserResponse) -> list[ClientSummary]:
    is_admin = is_platform_admin(user)
    with connect() as conn:
        rows = client_hub_repo.list_clients(conn, is_admin, user.id)
    return [ClientSummary(**row) for row in rows]


def create_client(payload: ClientCreateRequest, user: CurrentUserResponse) -> ClientPortalResponse:
    require_platform_admin(user)
    client_name = payload.name.strip()
    if not client_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome do cliente é obrigatório.")

    with connect() as conn:
        tenant_organization_id = workspaces_repo.find_platform_tenant_id(conn, user.id)
        if not tenant_organization_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tenant administrativo não encontrado para criar o cliente.",
            )
        organization_name = (payload.organization_name or client_name).strip()
        organization_slug = client_hub_repo.unique_org_slug(conn, payload.organization_slug or organization_name)
        organization_id = client_hub_repo.create_organization(
            conn,
            organization_name,
            organization_slug,
            tenant_organization_id,
        )
        client_id = client_hub_repo.create_client(
            conn,
            organization_id,
            client_name,
            payload.status,
            payload.responsible_name,
        )
        workspaces_repo.provision_client_workspace(
            conn,
            tenant_organization_id,
            organization_id,
            client_name,
            organization_slug,
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            organization_id,
            "client.created",
            {"client_id": str(client_id), "name": client_name},
        )

    return get_client_portal(client_id, user)


def archive_client(client_id: UUID, user: CurrentUserResponse) -> None:
    require_platform_admin(user)
    with connect() as conn:
        client = client_hub_repo.find_client_for_lifecycle(conn, client_id)
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
        if client["status"] == "archived" and client["workspace_status"] == "archived":
            return
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "client.archived",
            {"client_id": str(client_id), "name": client["name"]},
        )
        client_hub_repo.archive_client(conn, client_id, client["workspace_id"])


def purge_client(client_id: UUID, confirmation: str, user: CurrentUserResponse) -> None:
    require_platform_admin(user)
    with connect() as conn:
        client = client_hub_repo.find_client_for_lifecycle(conn, client_id)
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
        if client["status"] != "archived" or client["workspace_status"] != "archived":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Arquive o cliente antes do purge permanente.",
            )
        if confirmation.strip() != client["name"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A confirmação precisa corresponder exatamente ao nome do cliente.",
            )
        storage_keys = client_hub_repo.list_client_storage_keys(conn, client["organization_id"])
        try:
            for storage_key in storage_keys:
                delete_object(storage_key)
        except StorageNotConfiguredError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except StorageOperationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "client.purged",
            {
                "client_id": str(client_id),
                "name": client["name"],
                "storage_objects_deleted": len(storage_keys),
            },
        )
        client_hub_repo.purge_client_organization(conn, client["organization_id"])


def get_client_portal(client_id: UUID, user: CurrentUserResponse) -> ClientPortalResponse:
    is_admin = is_platform_admin(user)
    with connect() as conn:
        context = resolve_accessible_client(conn, client_id, user)
        resolved_client_id = context["id"]
        client = client_hub_repo.get_client_summary(conn, resolved_client_id, is_admin, user.id)
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")

        artifacts = client_hub_repo.list_artifacts(conn, client["organization_id"], is_admin)
        deliverables = client_hub_repo.list_deliverables(conn, client["organization_id"])
        approvals = client_hub_repo.list_approvals(conn, client["organization_id"])
        sync_runs = client_hub_repo.list_sync_runs(conn, client["organization_id"])
        audit_logs = client_hub_repo.list_audit_logs(conn, client["organization_id"])

    return ClientPortalResponse(
        client=ClientSummary(**client),
        artifacts=list(artifacts),
        deliverables=list(deliverables),
        approvals=list(approvals),
        sync_runs=list(sync_runs),
        audit_logs=list(audit_logs),
    )


def update_client(client_id: UUID, payload: ClientUpdateRequest, user: CurrentUserResponse) -> ClientPortalResponse:
    updates = payload.model_dump(exclude_unset=True)

    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="manage_config")
        resolved_client_id = client["id"]
        client_updates = {key: updates[key] for key in ("name", "status", "responsible_name") if key in updates}
        client_hub_repo.update_client(conn, resolved_client_id, client_updates)
        if "name" in client_updates:
            workspaces_repo.update_client_workspace_name(
                conn,
                client["organization_id"],
                client_updates["name"],
            )
        if "organization_name" in updates:
            client_hub_repo.update_organization_name(conn, client["organization_id"], updates["organization_name"])
        if updates.get("enabled_modules") is not None:
            requested = set(updates["enabled_modules"])
            invalid = requested - set(CLIENT_MODULES)
            if invalid:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Módulos desconhecidos: {', '.join(sorted(invalid))}.",
                )
            # Hub é o núcleo do portal do cliente; não pode ser desabilitado.
            modules = [module for module in CLIENT_MODULES if module in requested | {"hub"}]
            client_hub_repo.update_organization_modules(conn, client["organization_id"], modules)
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "client.updated",
            {"client_id": str(client_id), "fields": sorted(updates.keys())},
        )

    return get_client_portal(client_id, user)


def create_artifact(client_id: UUID, payload: ArtifactCreateRequest, user: CurrentUserResponse) -> ClientPortalResponse:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="manage_work")
        artifact_id = client_hub_repo.create_artifact(
            conn,
            client["organization_id"],
            payload.title,
            payload.kind,
            payload.visibility,
            payload.content,
            payload.url,
            user.id,
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "artifact.created",
            {"client_id": str(client_id), "artifact_id": str(artifact_id), "title": payload.title},
        )

    return get_client_portal(client_id, user)


def update_artifact(
    client_id: UUID,
    artifact_id: UUID,
    payload: ArtifactUpdateRequest,
    user: CurrentUserResponse,
) -> ClientPortalResponse:
    updates = payload.model_dump(exclude_unset=True)

    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="manage_work")
        if not client_hub_repo.update_artifact(conn, client["organization_id"], artifact_id, updates):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefato não encontrado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "artifact.updated",
            {"client_id": str(client_id), "artifact_id": str(artifact_id), "fields": sorted(updates.keys())},
        )

    return get_client_portal(client_id, user)


def delete_artifact(client_id: UUID, artifact_id: UUID, user: CurrentUserResponse) -> ClientPortalResponse:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="manage_work")
        if not client_hub_repo.delete_artifact(conn, client["organization_id"], artifact_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefato não encontrado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "artifact.deleted",
            {"client_id": str(client_id), "artifact_id": str(artifact_id)},
        )

    return get_client_portal(client_id, user)


def create_deliverable(client_id: UUID, payload: DeliverableCreateRequest, user: CurrentUserResponse) -> ClientPortalResponse:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="manage_work")
        deliverable_id = client_hub_repo.create_deliverable(
            conn,
            client["organization_id"],
            payload.title,
            payload.status,
            payload.due_at,
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "deliverable.created",
            {"client_id": str(client_id), "deliverable_id": str(deliverable_id), "title": payload.title},
        )

    return get_client_portal(client_id, user)


def update_deliverable(
    client_id: UUID,
    deliverable_id: UUID,
    payload: DeliverableUpdateRequest,
    user: CurrentUserResponse,
) -> ClientPortalResponse:
    updates = payload.model_dump(exclude_unset=True)

    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="manage_work")
        if not client_hub_repo.update_deliverable(conn, client["organization_id"], deliverable_id, updates):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega não encontrada.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "deliverable.updated",
            {"client_id": str(client_id), "deliverable_id": str(deliverable_id), "fields": sorted(updates.keys())},
        )

    return get_client_portal(client_id, user)


def delete_deliverable(client_id: UUID, deliverable_id: UUID, user: CurrentUserResponse) -> ClientPortalResponse:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="manage_work")
        if not client_hub_repo.delete_deliverable(conn, client["organization_id"], deliverable_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega não encontrada.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "deliverable.deleted",
            {"client_id": str(client_id), "deliverable_id": str(deliverable_id)},
        )

    return get_client_portal(client_id, user)


def create_approval(
    client_id: UUID,
    payload: ApprovalCreateRequest,
    user: CurrentUserResponse,
) -> ClientPortalResponse:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="manage_work")
        deliverable = client_hub_repo.get_deliverable(
            conn,
            client["organization_id"],
            payload.deliverable_id,
        )
        if not deliverable:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega não encontrada.")

        if client_hub_repo.get_pending_approval(conn, client["organization_id"], payload.deliverable_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta entrega já possui uma aprovação pendente.",
            )

        approval_id = client_hub_repo.create_approval(
            conn,
            client["organization_id"],
            payload.deliverable_id,
            user.id,
            payload.comment,
        )
        client_hub_repo.update_deliverable(
            conn,
            client["organization_id"],
            payload.deliverable_id,
            {"status": "waiting_approval"},
        )
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "approval.requested",
            {
                "approval_id": str(approval_id),
                "deliverable_id": str(payload.deliverable_id),
            },
        )

    return get_client_portal(client_id, user)


def decide_approval(
    client_id: UUID,
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    user: CurrentUserResponse,
) -> ClientPortalResponse:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, capability="approve")
        approval = client_hub_repo.get_approval(conn, client["organization_id"], approval_id)
        if not approval:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aprovação não encontrada.")
        if approval["status"] != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Aprovação já decidida.")

        client_hub_repo.decide_approval(conn, approval_id, payload.status, payload.comment, user.id)
        if approval["deliverable_id"]:
            next_status = "done" if payload.status == "approved" else "blocked"
            client_hub_repo.update_waiting_deliverable_status(conn, approval["deliverable_id"], next_status)
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "approval.decided",
            {"approval_id": str(approval_id), "status": payload.status},
        )

    return get_client_portal(client_id, user)


def list_leads(client_id: UUID, user: CurrentUserResponse) -> list[LeadSummary]:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "commercial")
        rows = client_hub_repo.list_leads(conn, client["organization_id"])
    return [LeadSummary(**row) for row in rows]


def create_lead(client_id: UUID, payload: LeadCreateRequest, user: CurrentUserResponse) -> list[LeadSummary]:
    lead_data = payload.model_dump()
    _require_non_empty(lead_data.get("name"), "Nome do lead é obrigatório.")
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "commercial", "manage_work")
        lead_id = client_hub_repo.create_lead(conn, client["organization_id"], lead_data)
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "lead.created",
            {"client_id": str(client_id), "lead_id": str(lead_id), "name": lead_data["name"]},
        )
    return list_leads(client_id, user)


def update_lead(
    client_id: UUID,
    lead_id: UUID,
    payload: LeadUpdateRequest,
    user: CurrentUserResponse,
) -> list[LeadSummary]:
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "commercial", "manage_work")
        if not client_hub_repo.update_lead(conn, client["organization_id"], lead_id, updates):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "lead.updated",
            {"client_id": str(client_id), "lead_id": str(lead_id), "fields": sorted(updates.keys())},
        )
    return list_leads(client_id, user)


def delete_lead(client_id: UUID, lead_id: UUID, user: CurrentUserResponse) -> list[LeadSummary]:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "commercial", "manage_work")
        if not client_hub_repo.delete_lead(conn, client["organization_id"], lead_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "lead.deleted",
            {"client_id": str(client_id), "lead_id": str(lead_id)},
        )
    return list_leads(client_id, user)


def list_financial_records(client_id: UUID, user: CurrentUserResponse) -> list[FinancialRecordSummary]:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "commercial")
        rows = client_hub_repo.list_financial_records(conn, client["organization_id"])
    return [FinancialRecordSummary(**row) for row in rows]


def create_financial_record(
    client_id: UUID,
    payload: FinancialRecordCreateRequest,
    user: CurrentUserResponse,
) -> list[FinancialRecordSummary]:
    record_data = payload.model_dump()
    _require_non_empty(record_data.get("title"), "Título financeiro é obrigatório.")
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "commercial", "manage_work")
        record_id = client_hub_repo.create_financial_record(conn, client["organization_id"], record_data)
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "financial_record.created",
            {"client_id": str(client_id), "record_id": str(record_id), "title": record_data["title"]},
        )
    return list_financial_records(client_id, user)


def update_financial_record(
    client_id: UUID,
    record_id: UUID,
    payload: FinancialRecordUpdateRequest,
    user: CurrentUserResponse,
) -> list[FinancialRecordSummary]:
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "commercial", "manage_work")
        if not client_hub_repo.update_financial_record(conn, client["organization_id"], record_id, updates):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro financeiro não encontrado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "financial_record.updated",
            {"client_id": str(client_id), "record_id": str(record_id), "fields": sorted(updates.keys())},
        )
    return list_financial_records(client_id, user)


def delete_financial_record(client_id: UUID, record_id: UUID, user: CurrentUserResponse) -> list[FinancialRecordSummary]:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "commercial", "manage_work")
        if not client_hub_repo.delete_financial_record(conn, client["organization_id"], record_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro financeiro não encontrado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "financial_record.deleted",
            {"client_id": str(client_id), "record_id": str(record_id)},
        )
    return list_financial_records(client_id, user)


def list_performance_metrics(client_id: UUID, user: CurrentUserResponse) -> list[PerformanceMetricSummary]:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "analytics")
        rows = client_hub_repo.list_performance_metrics(conn, client["organization_id"])
    return [PerformanceMetricSummary(**row) for row in rows]


def create_performance_metric(
    client_id: UUID,
    payload: PerformanceMetricCreateRequest,
    user: CurrentUserResponse,
) -> list[PerformanceMetricSummary]:
    metric_data = payload.model_dump()
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "analytics", "manage_work")
        metric_id = client_hub_repo.create_performance_metric(conn, client["organization_id"], metric_data)
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "performance_metric.created",
            {"client_id": str(client_id), "metric_id": str(metric_id), "metric": metric_data["metric"]},
        )
    return list_performance_metrics(client_id, user)


def update_performance_metric(
    client_id: UUID,
    metric_id: UUID,
    payload: PerformanceMetricUpdateRequest,
    user: CurrentUserResponse,
) -> list[PerformanceMetricSummary]:
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "analytics", "manage_work")
        if not client_hub_repo.update_performance_metric(conn, client["organization_id"], metric_id, updates):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Métrica não encontrada.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "performance_metric.updated",
            {"client_id": str(client_id), "metric_id": str(metric_id), "fields": sorted(updates.keys())},
        )
    return list_performance_metrics(client_id, user)


def delete_performance_metric(client_id: UUID, metric_id: UUID, user: CurrentUserResponse) -> list[PerformanceMetricSummary]:
    with connect() as conn:
        client = resolve_accessible_client(conn, client_id, user, "analytics", "manage_work")
        if not client_hub_repo.delete_performance_metric(conn, client["organization_id"], metric_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Métrica não encontrada.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            client["organization_id"],
            "performance_metric.deleted",
            {"client_id": str(client_id), "metric_id": str(metric_id)},
        )
    return list_performance_metrics(client_id, user)


def _require_non_empty(value: str | None, detail: str) -> None:
    if not value or not value.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def list_my_deliverables(user: CurrentUserResponse) -> list[dict]:
    with connect() as conn:
        return client_hub_repo.list_my_deliverables(
            conn,
            user.email,
            is_platform_admin(user),
            user.id,
        )


def get_cockpit_summary(user: CurrentUserResponse) -> CockpitPortfolioSummary:
    require_platform_admin(user)
    with connect() as conn:
        row = client_hub_repo.get_portfolio_summary(conn)
    return CockpitPortfolioSummary(**row)


def get_daily_brief(user: CurrentUserResponse) -> DailyBrief:
    """O resumo diário do cockpit — decisão 3, opção A.

    Reaproveita o apanhado que o cockpit já faz em vez de consultar de novo: o
    resumo é uma LEITURA do mesmo estado, e uma segunda consulta abriria a
    chance de os dois discordarem na mesma tela.
    """
    require_platform_admin(user)
    with connect() as conn:
        row = client_hub_repo.get_portfolio_summary(conn)
    return DailyBrief(
        generated_at=datetime.now(timezone.utc),
        **daily_brief.compose_brief(dict(row)),
    )


def get_portfolio_performance(user: CurrentUserResponse, days: int = 30) -> list[PortfolioPerformanceRow]:
    require_platform_admin(user)
    with connect() as conn:
        rows = client_hub_repo.get_portfolio_performance(conn, days)
    return [PortfolioPerformanceRow(**row) for row in rows]


def set_monthly_target(
    client_id: UUID,
    payload: MonthlyTargetRequest,
    user: CurrentUserResponse,
    days: int = 30,
) -> list[PortfolioPerformanceRow]:
    """Define a meta do mês do cliente e devolve o rollup já recalculado."""
    require_platform_admin(user)
    with connect() as conn:
        found = client_hub_repo.upsert_monthly_target(
            conn, client_id, payload.target_leads, payload.budget_cents
        )
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
        client_hub_repo.write_audit(
            conn,
            user.id,
            None,
            "client.monthly_target_set",
            {
                "client_id": str(client_id),
                "target_leads": payload.target_leads,
                "budget_cents": payload.budget_cents,
            },
        )
        rows = client_hub_repo.get_portfolio_performance(conn, days)
    return [PortfolioPerformanceRow(**row) for row in rows]
