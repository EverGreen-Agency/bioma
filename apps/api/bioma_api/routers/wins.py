from uuid import UUID

from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.wins import (
    WinCreate,
    WinDetectionResult,
    WinOverview,
    WinReaction,
    WinSummary,
    WinUpdate,
)
from bioma_api.services import wins as service

router = APIRouter(prefix="/wins", tags=["wins"])


@router.get("", response_model=list[WinSummary])
def list_wins(
    category: str | None = Query(default=None),
    workspace_id: UUID | None = Query(default=None),
    ceo_only: bool = Query(default=False),
    days: int | None = Query(default=None, ge=1, le=365),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[WinSummary]:
    """EG vê tudo; cliente vê só o que foi liberado do workspace dele."""
    return service.list_wins(category, workspace_id, ceo_only, days, user)


@router.get("/overview", response_model=WinOverview)
def overview(
    days: int = Query(default=30, ge=1, le=365),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WinOverview:
    return service.overview(days, user)


@router.post("", response_model=WinSummary, status_code=201)
def create(
    payload: WinCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WinSummary:
    """Registro manual — para o que não está em tabela nenhuma."""
    return service.create(payload, user)


@router.post("/detect", response_model=WinDetectionResult)
def detect(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WinDetectionResult:
    """Varre os detectores desde a última execução de cada um."""
    return service.detect(user)


@router.get("/export/foton")
def export_for_foton(
    days: int = Query(default=90, ge=1, le=365),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict:
    """Pacote de vitórias do CEO — exportação explícita, com trilha de auditoria."""
    return service.export_for_foton(days, user)


@router.patch("/{win_id}", response_model=WinSummary)
def update(
    win_id: UUID,
    payload: WinUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WinSummary:
    return service.update(win_id, payload, user)


@router.post("/{win_id}/react", response_model=WinSummary)
def react(
    win_id: UUID,
    payload: WinReaction,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> WinSummary:
    return service.react(win_id, payload, user)


@router.delete("/{win_id}")
def remove(
    win_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict[str, str]:
    return service.remove(win_id, user)
