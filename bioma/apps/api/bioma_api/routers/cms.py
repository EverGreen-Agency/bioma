from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.cms import (
    ArtifactPublication,
    CmsTarget,
    CmsTargetCheck,
    CmsTargetCreate,
    CmsTargetUpdate,
    PublicationPreview,
    PublishRequest,
)
from bioma_api.services import cms as service

# Sob `/studio`, como o resto da decisão 8 — e pelo mesmo motivo de lá:
# `/workspaces/{id}/artifacts` já é do client_hub, e registrar de novo daria
# 201 com corpo errado, em silêncio.
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}/studio", tags=["cms"])


@workspace_router.get("/cms-targets", response_model=list[CmsTarget])
def list_targets(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[CmsTarget]:
    return service.list_targets(workspace_id, user)


@workspace_router.post("/cms-targets", response_model=CmsTarget, status_code=201)
def create_target(
    workspace_id: UUID,
    payload: CmsTargetCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CmsTarget:
    return service.create_target(workspace_id, payload, user)


@workspace_router.patch("/cms-targets/{target_id}", response_model=CmsTarget)
def update_target(
    workspace_id: UUID,
    target_id: UUID,
    payload: CmsTargetUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CmsTarget:
    return service.update_target(workspace_id, target_id, payload, user)


@workspace_router.post("/cms-targets/{target_id}/check", response_model=CmsTargetCheck)
def check_target(
    workspace_id: UUID,
    target_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> CmsTargetCheck:
    """Testa a credencial contra o site sem escrever nada lá.

    Devolve 200 mesmo quando a credencial é inválida: falhar o teste não é erro
    da requisição, é o resultado dela. `ok=false` com o motivo é mais útil que
    um 4xx que a tela teria que destrinchar.
    """
    return service.check_target(workspace_id, target_id, user)


@workspace_router.post("/artifacts/{artifact_id}/publish-preview", response_model=PublicationPreview)
def preview(
    workspace_id: UUID,
    artifact_id: UUID,
    payload: PublishRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> PublicationPreview:
    """O que seria enviado, sem enviar. POST porque o corpo carrega as opções."""
    return service.preview_publication(workspace_id, artifact_id, payload, user)


@workspace_router.post("/artifacts/{artifact_id}/publish", response_model=ArtifactPublication, status_code=201)
def publish(
    workspace_id: UUID,
    artifact_id: UUID,
    payload: PublishRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ArtifactPublication:
    return service.publish(workspace_id, artifact_id, payload, user)


@workspace_router.get("/artifacts/{artifact_id}/publications", response_model=list[ArtifactPublication])
def list_publications(
    workspace_id: UUID,
    artifact_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[ArtifactPublication]:
    return service.list_publications(workspace_id, artifact_id, user)
