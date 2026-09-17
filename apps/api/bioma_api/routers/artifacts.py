from uuid import UUID

from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.artifacts import (
    ContentQualityReport,
    ContentQualityRequest,
    StudioArtifactCreate,
    StudioArtifactFromRun,
    StudioArtifactDetail,
    StudioArtifactKindCount,
    StudioArtifactStatusUpdate,
    StudioArtifact,
    StudioArtifactVersionCreate,
)
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services import artifacts as service

# `/studio` e não `/artifacts`: `client_hub.workspace_router` já registra
# `/workspaces/{client_id}/artifacts` (o CRUD antigo, que devolve o portal
# inteiro do cliente). Como ele é incluído antes, ficaria com a rota e este
# router nunca responderia — colisão silenciosa, com 201 e corpo errado.
# O nome também diz o que a superfície é: a vista do Estúdio.
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}/studio", tags=["artifacts"])
router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@workspace_router.get("", response_model=list[StudioArtifact])
def list_artifacts(
    workspace_id: UUID,
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[StudioArtifact]:
    """A vista do Estúdio: o que a conversa produziu, organizado."""
    return service.list_artifacts(workspace_id, user, kind, status)


@workspace_router.get("/kinds", response_model=list[StudioArtifactKindCount])
def list_kinds(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[StudioArtifactKindCount]:
    """Tipos que existem neste workspace. O catálogo é aberto, então a tela
    descobre em vez de partir de uma lista fixa."""
    return service.list_kinds(workspace_id, user)


@workspace_router.post("", response_model=StudioArtifactDetail, status_code=201)
def create_artifact(
    workspace_id: UUID,
    payload: StudioArtifactCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> StudioArtifactDetail:
    return service.create_artifact(workspace_id, payload, user)


@workspace_router.post("/content-quality", response_model=ContentQualityReport)
def evaluate_quality(
    workspace_id: UUID,
    payload: ContentQualityRequest,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ContentQualityReport:
    """Avalia prontidao SEO/GEO de um texto — inclusive de rascunho nao salvo.

    POST porque o texto vai no corpo (query string tem limite), nao porque
    grava algo: a rota e um calculo puro e nao tem efeito colateral.
    """
    return service.evaluate_quality(workspace_id, payload, user)


@router.post("/from-run/{run_id}", response_model=StudioArtifactDetail, status_code=201)
def save_from_run(
    run_id: UUID,
    payload: StudioArtifactFromRun,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> StudioArtifactDetail:
    """Salva a resposta de uma execução do copiloto como artefato.

    O elo entre os dois sistemas: `thread_id` e `run_id` são deduzidos da
    execução, nunca aceitos do cliente — procedência que mente é pior que
    procedência ausente. Passando `artifact_id`, vira a próxima versão.
    """
    return service.save_from_run(run_id, payload, user)


@router.get("/{artifact_id}", response_model=StudioArtifactDetail)
def get_artifact(
    artifact_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> StudioArtifactDetail:
    return service.get_artifact(artifact_id, user)


@router.post("/{artifact_id}/versions", response_model=StudioArtifactDetail, status_code=201)
def add_version(
    artifact_id: UUID,
    payload: StudioArtifactVersionCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> StudioArtifactDetail:
    """Nova versão — nunca sobrescreve a anterior."""
    return service.add_version(artifact_id, payload, user)


@router.patch("/{artifact_id}/status", response_model=StudioArtifactDetail)
def set_status(
    artifact_id: UUID,
    payload: StudioArtifactStatusUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> StudioArtifactDetail:
    return service.set_status(artifact_id, payload, user)
