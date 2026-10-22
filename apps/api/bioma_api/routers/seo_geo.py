from uuid import UUID

from fastapi import APIRouter, Depends, status

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.seo_geo import (
    SeoGeoAuditRequest,
    SeoGeoAuditResponse,
    SeoGeoAuditSummary,
)
from bioma_api.services import seo_geo as service

router = APIRouter(tags=["seo-geo"])
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}/seo-geo", tags=["seo-geo"])


@router.post("/seo-geo/preview", response_model=SeoGeoAuditResponse)
def preview_audit(
    payload: SeoGeoAuditRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> SeoGeoAuditResponse:
    """Executa varredura ao vivo da URL retornando scores SEO/GEO e recomendações sem persistir."""
    return service.preview_audit(payload)


@workspace_router.get("/audits", response_model=list[SeoGeoAuditSummary])
def list_workspace_audits(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SeoGeoAuditSummary]:
    """Lista histórico de auditorias de SEO e GEO do workspace."""
    return service.list_audits(workspace_id, user)


@workspace_router.post("/audits", response_model=SeoGeoAuditResponse, status_code=status.HTTP_201_CREATED)
def create_workspace_audit(
    workspace_id: UUID,
    payload: SeoGeoAuditRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> SeoGeoAuditResponse:
    """Executa auditoria ao vivo e persiste o relatório no banco de dados do workspace."""
    return service.create_and_store_audit(workspace_id, payload, user)


@workspace_router.get("/audits/{audit_id}", response_model=SeoGeoAuditResponse)
def get_workspace_audit(
    workspace_id: UUID,
    audit_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> SeoGeoAuditResponse:
    """Recupera os detalhes completos de uma auditoria persistida."""
    return service.get_audit(workspace_id, audit_id, user)


@workspace_router.delete("/audits/{audit_id}")
def delete_workspace_audit(
    workspace_id: UUID,
    audit_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    """Remove uma auditoria do histórico."""
    return service.delete_audit(workspace_id, audit_id, user)
