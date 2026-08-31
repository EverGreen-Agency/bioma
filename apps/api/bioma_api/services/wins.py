"""Mural de vitórias: registro manual, detecção automática e exportação.

Escopo: leitura e escrita são da EG. A exceção é a vitória marcada
`visibility = 'client'`, que aparece no hub daquele cliente — e só aparece
porque alguém decidiu mostrar, nunca por padrão.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import wins as repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.wins import (
    WinCreate,
    WinDetectionResult,
    WinOverview,
    WinReaction,
    WinSummary,
    WinUpdate,
)
from bioma_api.win_detectors import DETECTORS, FIRST_SCAN_WINDOW


def create(payload: WinCreate, user: CurrentUserResponse) -> WinSummary:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.create(
            conn,
            {
                **payload.model_dump(),
                "source": "manual",
                "occurred_at": payload.occurred_at or datetime.now(timezone.utc),
                "credited_user_ids": [str(item) for item in payload.credited_user_ids],
                "created_by": user.id,
            },
        )
    if not row:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vitória já registrada.")
    return WinSummary(**row)


def list_wins(
    category: str | None,
    workspace_id: UUID | None,
    ceo_only: bool,
    days: int | None,
    user: CurrentUserResponse,
) -> list[WinSummary]:
    """EG vê tudo; usuário de cliente vê só o que foi liberado do workspace dele.

    O filtro de visibilidade é do backend de propósito: esconder no frontend
    faria a vitória interna viajar no payload do cliente.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days) if days else None
    with connect() as conn:
        if is_platform_admin(user):
            rows = repo.list_wins(conn, category, workspace_id, ceo_only, since)
        else:
            if not workspace_id:
                return []
            client = workspaces_repo.find_accessible_client(conn, workspace_id, False, user.id)
            if not client:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
            rows = repo.list_wins(conn, category, workspace_id, False, since, visibility="client")
    return [WinSummary(**row) for row in rows]


def update(win_id: UUID, payload: WinUpdate, user: CurrentUserResponse) -> WinSummary:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.update(conn, win_id, payload.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vitória não encontrada.")
    return WinSummary(**row)


def react(win_id: UUID, payload: WinReaction, user: CurrentUserResponse) -> WinSummary:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.react(conn, win_id, payload.emoji, user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vitória não encontrada.")
    return WinSummary(**row)


def remove(win_id: UUID, user: CurrentUserResponse) -> dict[str, str]:
    require_platform_admin(user)
    with connect() as conn:
        if not repo.delete(conn, win_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vitória não encontrada.")
    return {"status": "deleted"}


def detect(user: CurrentUserResponse) -> WinDetectionResult:
    """Roda todos os detectores desde a última varredura de cada um.

    Um detector que quebra não derruba os outros: o erro fica registrado no
    resultado e os demais seguem. Detector novo com bug não pode significar
    mural em branco.
    """
    require_platform_admin(user)
    created = 0
    duplicates = 0
    by_rule: dict[str, int] = {}
    errors: dict[str, str] = {}

    with connect() as conn:
        for rule_key, detector in DETECTORS.items():
            since = repo.last_scan(conn, rule_key) or datetime.now(timezone.utc) - FIRST_SCAN_WINDOW
            try:
                candidates = detector(conn, since)
            except Exception as exc:  # noqa: BLE001 — ver docstring
                errors[rule_key] = f"{type(exc).__name__}: {exc}"[:300]
                continue

            found = 0
            for candidate in candidates:
                if repo.create(conn, candidate):
                    created += 1
                    found += 1
                else:
                    duplicates += 1
            by_rule[rule_key] = found
            repo.record_scan(conn, rule_key, found)

        if created:
            client_hub_repo.write_audit(
                conn, user.id, None, "wins.detected", {"created": created, "by_rule": by_rule}
            )

    return WinDetectionResult(
        scanned_rules=len(DETECTORS),
        created=created,
        skipped_duplicates=duplicates,
        by_rule=by_rule,
        errors=errors,
    )


def overview(days: int, user: CurrentUserResponse) -> WinOverview:
    require_platform_admin(user)
    with connect() as conn:
        return WinOverview(**repo.summary(conn, days))


def export_for_foton(days: int, user: CurrentUserResponse) -> dict:
    """Pacote de vitórias do CEO para o Fóton.

    Segue o princípio do handoff do Context Engine: a integração Bioma ↔ Fóton é
    **exportação explícita com escopo e finalidade**, nunca cópia silenciosa. Vai
    só o que está marcado `is_ceo`, e a exportação fica na trilha de auditoria —
    dá para responder depois "o que saiu do Bioma, quando e para quê".
    """
    require_platform_admin(user)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with connect() as conn:
        rows = repo.list_wins(conn, None, None, True, since, limit=500)
        client_hub_repo.write_audit(
            conn, user.id, None, "wins.exported_to_foton", {"days": days, "count": len(rows)}
        )
    return {
        "scope": "ceo_wins",
        "purpose": "contexto pessoal do CEO no Fóton",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": days,
        "count": len(rows),
        "wins": [
            {
                "title": row["title"],
                "description": row["description"],
                "category": row["category"],
                "source": row["source"],
                "occurred_at": row["occurred_at"].isoformat(),
                "metric": (
                    {"value": float(row["metric_value"]), "unit": row["metric_unit"]}
                    if row["metric_value"] is not None
                    else None
                ),
                # A evidência acompanha: no Fóton, uma vitória sem origem vira
                # anedota. Com ela, dá para voltar ao Bioma e conferir.
                "evidence": row["evidence"],
            }
            for row in rows
        ],
    }
