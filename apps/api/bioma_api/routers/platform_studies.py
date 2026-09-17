from uuid import UUID

from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.platform_studies import (
    PlatformStudyBulkCreate,
    PlatformStudyCreate,
    PlatformStudyOverview,
    PlatformStudySummary,
    PlatformStudyVerdict,
)
from bioma_api.services import platform_studies as service

router = APIRouter(prefix="/platform-studies", tags=["platform-studies"])


@router.get("", response_model=list[PlatformStudySummary])
def list_platforms(
    research_status: str | None = Query(default=None),
    verdict: str | None = Query(default=None),
    target: str | None = Query(default=None),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[PlatformStudySummary]:
    """Fila ordenada por prioridade de teste — quem pode mudar a estratégia primeiro."""
    return service.list_platforms(research_status, verdict, target, user)


@router.get("/overview", response_model=PlatformStudyOverview)
def overview(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> PlatformStudyOverview:
    """Agregado: quantas ameaçam o escopo do Bioma, e quais."""
    return service.overview(user)


@router.post("", response_model=PlatformStudySummary, status_code=201)
def add_platform(
    payload: PlatformStudyCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> PlatformStudySummary:
    return service.add_platform(payload, user)


@router.post("/bulk", response_model=list[PlatformStudySummary], status_code=201)
def add_many(
    payload: PlatformStudyBulkCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[PlatformStudySummary]:
    """Cola a lista inteira. Captura é barata; a pesquisa é disparada uma a uma."""
    return service.add_many(payload, user)


@router.get("/{study_id}", response_model=PlatformStudySummary)
def get_platform(
    study_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> PlatformStudySummary:
    return service.get_platform(study_id, user)


@router.post("/{study_id}/research", response_model=PlatformStudySummary)
def research(
    study_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> PlatformStudySummary:
    """Busca as páginas públicas e produz a leitura estruturada com fontes."""
    return service.research(study_id, user)


@router.post("/{study_id}/verdict", response_model=PlatformStudySummary)
def decide(
    study_id: UUID,
    payload: PlatformStudyVerdict,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> PlatformStudySummary:
    return service.decide(study_id, payload, user)


@router.delete("/{study_id}")
def remove(
    study_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, str]:
    return service.remove(study_id, user)
