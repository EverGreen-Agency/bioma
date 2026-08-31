"""Estado efetivo das features por organização.

Leitura é liberada para quem enxerga a organização (o cliente precisa saber que
existe algo "em breve"); escrita é EG-only.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import check_organization_access, is_platform_admin, require_platform_admin
from bioma_api.db import connect
from bioma_api.feature_flags import FEATURE_CATALOG, default_state, is_accessible
from bioma_api.repositories import feature_flags as repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.feature_flags import FeatureFlag, FeatureFlagUpsert


def list_flags(organization_id: UUID, user: CurrentUserResponse) -> list[FeatureFlag]:
    if not is_platform_admin(user):
        check_organization_access(user, organization_id)

    with connect() as conn:
        overrides = {row["feature_key"]: row for row in repo.list_for_organization(conn, organization_id)}

    flags: list[FeatureFlag] = []
    for feature_key, entry in FEATURE_CATALOG.items():
        override = overrides.get(feature_key)
        state = override["state"] if override else default_state(feature_key)
        flags.append(
            FeatureFlag(
                feature_key=feature_key,
                label=entry["label"],
                description=entry["description"],
                state=state,  # type: ignore[arg-type]
                is_override=override is not None,
                accessible=is_accessible(state),  # type: ignore[arg-type]
                note=override["note"] if override else None,
                updated_at=override["updated_at"] if override else None,
            )
        )
    return flags


def upsert_flag(organization_id: UUID, payload: FeatureFlagUpsert, user: CurrentUserResponse) -> list[FeatureFlag]:
    require_platform_admin(user)
    if payload.feature_key not in FEATURE_CATALOG:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Feature desconhecida: {payload.feature_key}. O catálogo vive em bioma_api/feature_flags.py.",
        )
    with connect() as conn:
        repo.upsert(conn, organization_id, payload.feature_key, payload.state, payload.note, user.id)
    return list_flags(organization_id, user)


def clear_flag(organization_id: UUID, feature_key: str, user: CurrentUserResponse) -> list[FeatureFlag]:
    """Volta a feature ao default do catálogo (remove a exceção)."""
    require_platform_admin(user)
    with connect() as conn:
        repo.clear(conn, organization_id, feature_key)
    return list_flags(organization_id, user)


def assert_feature_accessible(organization_id: UUID, feature_key: str) -> None:
    """Gate de backend. A UI já esconde, mas esconder não é proteger."""
    with connect() as conn:
        overrides = {row["feature_key"]: row for row in repo.list_for_organization(conn, organization_id)}
    override = overrides.get(feature_key)
    state = override["state"] if override else default_state(feature_key)
    if not is_accessible(state):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta funcionalidade ainda não está liberada para este cliente.",
        )
