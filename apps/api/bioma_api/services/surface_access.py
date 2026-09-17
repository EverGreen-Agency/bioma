"""Acesso e visibilidade por superfície — leitura efetiva e administração.

Decisão 11. A resolução em si é pura e mora em `bioma_api.surface_access`; aqui
só se busca o que ela precisa e se aplica o gate de escrita.

Regra de quem pode mexer: **grant é EG-only, preferência é de cada um.** Um
usuário pode esconder o que quiser para si e não pode conceder nada — nem para
si nem para outros.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api import surface_access as resolver
from bioma_api import surfaces
from bioma_api.access import is_platform_admin, is_platform_member, require_platform_admin
from bioma_api.db import connect
from bioma_api.feature_flags import FEATURE_CATALOG, default_state, is_accessible
from bioma_api.repositories import feature_flags as flags_repo
from bioma_api.repositories import surface_access as repo
from bioma_api.repositories import teams as teams_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.surface_access import (
    SurfaceAccessEntry,
    SurfaceCatalogEntry,
    SurfaceGrantEntry,
    SurfaceGrantUpsert,
)


def _validate_key(surface_key: str) -> None:
    if not surfaces.is_known(surface_key):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Superfície desconhecida: {surface_key}. O catálogo vive em bioma_api/surfaces.py.",
        )


def _inaccessible_features(conn, user: CurrentUserResponse) -> set[str]:
    """Features que NENHUMA organização da pessoa tem liberadas.

    União, não interseção: quem pertence a duas organizações e tem a feature
    liberada numa delas continua vendo a tela. Bloquear pelo denominador mais
    restritivo faria uma organização nova e vazia derrubar acessos existentes.
    """
    if is_platform_member(user):
        return set()

    accessible: set[str] = set()
    for organization in user.organizations:
        overrides = {row["feature_key"]: row["state"] for row in flags_repo.list_for_organization(conn, organization.id)}
        for feature_key in FEATURE_CATALOG:
            state = overrides.get(feature_key) or default_state(feature_key)
            if is_accessible(state):  # type: ignore[arg-type]
                accessible.add(feature_key)
    return set(FEATURE_CATALOG) - accessible


def _enabled_modules(user: CurrentUserResponse) -> set[str]:
    modules = {module for organization in user.organizations for module in organization.enabled_modules}
    modules.add("hub")  # núcleo: o backend força isso em `require_client_module` também
    return modules


def _resolve(conn, user: CurrentUserResponse) -> list[resolver.SurfaceAccess]:
    # Visibilidade usa "pertence à EG", não "administra a EG" (0090): quem é
    # `eg_member` enxerga as telas internas. O que ele NÃO pode é escrever —
    # e isso continua guardado por `require_platform_admin` em cada serviço.
    is_eg = is_platform_member(user)

    team_rows: dict[str, list[tuple[str, str, str | None]]] = {}
    user_rows: dict[str, resolver.SurfaceGrant] = {}
    for row in repo.list_grants_for_user(conn, user.id):
        key = row["surface_key"]
        if not surfaces.is_known(key):
            continue  # superfície aposentada: linha órfã não decide nada
        if row["user_id"] is not None:
            user_rows[key] = resolver.SurfaceGrant(
                effect=row["effect"], subject_label=user.display_name, note=row["note"]
            )
        else:
            team_rows.setdefault(key, []).append((row["effect"], row["team_name"] or "sem nome", row["note"]))

    team_grants = {key: grant for key, value in team_rows.items() if (grant := resolver.merge_team_grants(value))}

    return resolver.resolve_all(
        is_eg_admin=is_eg,
        enabled_modules=_enabled_modules(user),
        inaccessible_features=_inaccessible_features(conn, user),
        team_grants=team_grants,
        user_grants=user_rows,
        hidden_keys=set(repo.list_hidden_keys(conn, user.id)),
    )


def _to_entry(access: resolver.SurfaceAccess) -> SurfaceAccessEntry:
    return SurfaceAccessEntry(
        surface_key=access.surface_key,
        label=access.label,
        group=access.group,
        parent=access.parent,
        locked=access.locked,
        allowed=access.allowed,
        visible=access.visible,
        can_prefer=access.can_prefer,
        reason=access.reason,  # type: ignore[arg-type]
        detail=access.detail,
        sources=access.sources,
    )


def list_my_surfaces(user: CurrentUserResponse) -> list[SurfaceAccessEntry]:
    with connect() as conn:
        return [_to_entry(access) for access in _resolve(conn, user)]


def set_my_preference(user: CurrentUserResponse, surface_key: str, hidden: bool) -> list[SurfaceAccessEntry]:
    _validate_key(surface_key)
    if hidden and surfaces.is_locked(surface_key):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Esta tela não pode ser ocultada — sem ela você ficaria sem home.",
        )

    with connect() as conn:
        if hidden:
            # Esconder o que já é negado não é erro, mas também não deve gravar
            # linha: a pessoa acharia que escolheu algo que a permissão já
            # decidia, e "reexibir" depois não devolveria nada.
            current = {access.surface_key: access for access in _resolve(conn, user)}
            access = current.get(surface_key)
            if access is not None and not access.allowed:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Você já não tem acesso a esta tela. {access.detail}",
                )
            repo.hide(conn, user.id, surface_key)
        else:
            repo.unhide(conn, user.id, surface_key)
        return [_to_entry(access) for access in _resolve(conn, user)]


def assert_surface_allowed(user: CurrentUserResponse, surface_key: str) -> None:
    """Gate de backend para uma superfície.

    Existe porque esconder não é proibir: para cliente, sumir do menu sem
    fechar a rota é organização visual vendida como segurança.
    """
    _validate_key(surface_key)
    with connect() as conn:
        for access in _resolve(conn, user):
            if access.surface_key == surface_key:
                if not access.allowed:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=access.detail)
                return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tela indisponível para o seu acesso.")


def catalog(user: CurrentUserResponse) -> list[SurfaceCatalogEntry]:
    require_platform_admin(user)
    return [
        SurfaceCatalogEntry(
            surface_key=key,
            label=entry.get("label", key),
            group=entry.get("group", "Outros"),
            parent=entry.get("parent"),
            scope=entry.get("scope", "both"),
            locked=bool(entry.get("locked")),
            module=entry.get("module"),
            feature_key=entry.get("feature_key"),
        )
        for key, entry in surfaces.SURFACE_CATALOG.items()
    ]


def _grant_entry(row) -> SurfaceGrantEntry:
    entry = surfaces.SURFACE_CATALOG.get(row["surface_key"], {})
    return SurfaceGrantEntry(
        id=row["id"],
        surface_key=row["surface_key"],
        # Chave órfã (superfície aposentada) aparece rotulada, não some: alguém
        # precisa enxergar a linha para limpá-la.
        label=entry.get("label", f"{row['surface_key']} (superfície desconhecida)"),
        group=entry.get("group", "Desconhecido"),
        team_id=row["team_id"],
        user_id=row["user_id"],
        effect=row["effect"],
        note=row["note"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_team_grants(team_id: UUID, user: CurrentUserResponse) -> list[SurfaceGrantEntry]:
    require_platform_admin(user)
    with connect() as conn:
        if not teams_repo.find_team(conn, team_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipe não encontrada.")
        return [_grant_entry(row) for row in repo.list_grants_for_team(conn, team_id)]


def upsert_team_grant(team_id: UUID, payload: SurfaceGrantUpsert, user: CurrentUserResponse) -> list[SurfaceGrantEntry]:
    require_platform_admin(user)
    _validate_key(payload.surface_key)
    with connect() as conn:
        if not teams_repo.find_team(conn, team_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipe não encontrada.")
        repo.upsert_team_grant(conn, team_id, payload.surface_key, payload.effect, payload.note, user.id)
        return [_grant_entry(row) for row in repo.list_grants_for_team(conn, team_id)]


def clear_team_grant(team_id: UUID, surface_key: str, user: CurrentUserResponse) -> list[SurfaceGrantEntry]:
    require_platform_admin(user)
    with connect() as conn:
        repo.clear_team_grant(conn, team_id, surface_key)
        return [_grant_entry(row) for row in repo.list_grants_for_team(conn, team_id)]


def list_user_grants(target_user_id: UUID, user: CurrentUserResponse) -> list[SurfaceGrantEntry]:
    require_platform_admin(user)
    with connect() as conn:
        return [_grant_entry(row) for row in repo.list_grants_for_subject_user(conn, target_user_id)]


def upsert_user_grant(
    target_user_id: UUID, payload: SurfaceGrantUpsert, user: CurrentUserResponse
) -> list[SurfaceGrantEntry]:
    require_platform_admin(user)
    _validate_key(payload.surface_key)
    with connect() as conn:
        repo.upsert_user_grant(conn, target_user_id, payload.surface_key, payload.effect, payload.note, user.id)
        return [_grant_entry(row) for row in repo.list_grants_for_subject_user(conn, target_user_id)]


def clear_user_grant(target_user_id: UUID, surface_key: str, user: CurrentUserResponse) -> list[SurfaceGrantEntry]:
    require_platform_admin(user)
    with connect() as conn:
        repo.clear_user_grant(conn, target_user_id, surface_key)
        return [_grant_entry(row) for row in repo.list_grants_for_subject_user(conn, target_user_id)]
