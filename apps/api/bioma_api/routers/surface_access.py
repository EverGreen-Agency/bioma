from uuid import UUID

from fastapi import APIRouter, Depends

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.surface_access import (
    SurfaceAccessEntry,
    SurfaceCatalogEntry,
    SurfaceGrantEntry,
    SurfaceGrantUpsert,
    SurfacePreferenceUpdate,
)
from bioma_api.services import surface_access as service

router = APIRouter(tags=["surface-access"])


@router.get("/me/surfaces", response_model=list[SurfaceAccessEntry])
def my_surfaces(user: CurrentUserResponse = Depends(current_user_from_request)) -> list[SurfaceAccessEntry]:
    """O que esta pessoa enxerga, e por quê.

    Uma chamada só devolve decisão e explicação juntas — é o que permite a tela
    responder "por que não vejo o RH?" sem uma segunda rota que poderia
    discordar da primeira.
    """
    return service.list_my_surfaces(user)


@router.put("/me/surfaces/preference", response_model=list[SurfaceAccessEntry])
def set_preference(
    payload: SurfacePreferenceUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SurfaceAccessEntry]:
    """Preferência pessoal: só esconde o que já era permitido."""
    return service.set_my_preference(user, payload.surface_key, payload.hidden)


@router.get("/surfaces/catalog", response_model=list[SurfaceCatalogEntry])
def catalog(user: CurrentUserResponse = Depends(current_user_from_request)) -> list[SurfaceCatalogEntry]:
    return service.catalog(user)


@router.get("/teams/{team_id}/surfaces", response_model=list[SurfaceGrantEntry])
def team_grants(
    team_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SurfaceGrantEntry]:
    return service.list_team_grants(team_id, user)


@router.put("/teams/{team_id}/surfaces", response_model=list[SurfaceGrantEntry])
def upsert_team_grant(
    team_id: UUID,
    payload: SurfaceGrantUpsert,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SurfaceGrantEntry]:
    return service.upsert_team_grant(team_id, payload, user)


@router.delete("/teams/{team_id}/surfaces/{surface_key}", response_model=list[SurfaceGrantEntry])
def clear_team_grant(
    team_id: UUID,
    surface_key: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SurfaceGrantEntry]:
    return service.clear_team_grant(team_id, surface_key, user)


@router.get("/users/{target_user_id}/surfaces", response_model=list[SurfaceGrantEntry])
def user_grants(
    target_user_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SurfaceGrantEntry]:
    return service.list_user_grants(target_user_id, user)


@router.put("/users/{target_user_id}/surfaces", response_model=list[SurfaceGrantEntry])
def upsert_user_grant(
    target_user_id: UUID,
    payload: SurfaceGrantUpsert,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SurfaceGrantEntry]:
    return service.upsert_user_grant(target_user_id, payload, user)


@router.delete("/users/{target_user_id}/surfaces/{surface_key}", response_model=list[SurfaceGrantEntry])
def clear_user_grant(
    target_user_id: UUID,
    surface_key: str,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[SurfaceGrantEntry]:
    return service.clear_user_grant(target_user_id, surface_key, user)
