from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import certifications as cert_repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import teams as teams_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.certifications import (
    CertificationCreateRequest,
    CertificationSummary,
    CertificationUpdateRequest,
)


def _tenant_id(conn) -> UUID:
    tenant_id = workspaces_repo.find_eg_tenant_id(conn)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant administrativo não encontrado.")
    return tenant_id


def _require_tenant_manager(conn, tenant_organization_id: UUID, user: CurrentUserResponse) -> None:
    if is_platform_admin(user) or teams_repo.can_manage_tenant(conn, tenant_organization_id, user.id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente para gestão de certificações.")


def list_certifications(user: CurrentUserResponse, user_id: UUID | None = None) -> list[CertificationSummary]:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        if user_id is not None and user_id == user.id:
            pass  # qualquer usuário pode ver as próprias certificações
        else:
            _require_tenant_manager(conn, tenant_id, user)
        rows = cert_repo.list_certifications(conn, tenant_id, user_id)
    return [CertificationSummary(**row) for row in rows]


def create_certification(payload: CertificationCreateRequest, user: CurrentUserResponse) -> CertificationSummary:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        row = cert_repo.create_certification(conn, tenant_id, user.id, payload.model_dump())
        client_hub_repo.write_audit(conn, user.id, tenant_id, "certification.created", {
            "certification_id": str(row["id"]), "provider": row["provider"], "name": row["name"],
        })
    return CertificationSummary(**row)


def update_certification(certification_id: UUID, payload: CertificationUpdateRequest, user: CurrentUserResponse) -> CertificationSummary:
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        row = cert_repo.update_certification(conn, tenant_id, certification_id, updates)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificação não encontrada.")
        client_hub_repo.write_audit(conn, user.id, tenant_id, "certification.updated", {"certification_id": str(certification_id), "fields": sorted(updates)})
    return CertificationSummary(**row)


def delete_certification(certification_id: UUID, user: CurrentUserResponse) -> None:
    with connect() as conn:
        tenant_id = _tenant_id(conn)
        _require_tenant_manager(conn, tenant_id, user)
        if not cert_repo.delete_certification(conn, tenant_id, certification_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificação não encontrada.")
        client_hub_repo.write_audit(conn, user.id, tenant_id, "certification.deleted", {"certification_id": str(certification_id)})
