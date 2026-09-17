"""Estudo de plataformas: da URL colada à decisão de build vs. buy.

Escopo: só EG. Isto é decisão sobre o próprio produto, não conteúdo de cliente.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.feature_flags import FEATURE_CATALOG
from bioma_api.model_pricing import cost_cents
from bioma_api.repositories import platform_studies as repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.platform_studies import (
    PlatformStudyBulkCreate,
    PlatformStudyCreate,
    PlatformStudyOverview,
    PlatformStudySummary,
    PlatformStudyVerdict,
)
from bioma_api.worker_bridge import platform_study_analyze_safe, platform_study_helpers


def add_platform(payload: PlatformStudyCreate, user: CurrentUserResponse) -> PlatformStudySummary:
    require_platform_admin(user)
    derive_name, _ = platform_study_helpers()
    with connect() as conn:
        row = repo.add(conn, payload.url, derive_name(payload.url), payload.targets, payload.added_note, user.id)
    return PlatformStudySummary(**row)


def add_many(payload: PlatformStudyBulkCreate, user: CurrentUserResponse) -> list[PlatformStudySummary]:
    """Cola a lista inteira. Não pesquisa nada — capturar é barato, pesquisar custa.

    A separação é de propósito: a primeira necessidade é não perder a lista.
    Disparar 78 análises no ato gastaria dezenas de reais antes de alguém decidir
    se todas valem a análise.
    """
    require_platform_admin(user)
    derive_name, _ = platform_study_helpers()
    created: list[PlatformStudySummary] = []
    with connect() as conn:
        for raw in payload.urls:
            url = PlatformStudyCreate(url=raw).url
            row = repo.add(conn, url, derive_name(url), payload.targets, None, user.id)
            created.append(PlatformStudySummary(**row))
    return created


def list_platforms(
    research_status: str | None, verdict: str | None, target: str | None, user: CurrentUserResponse
) -> list[PlatformStudySummary]:
    require_platform_admin(user)
    with connect() as conn:
        rows = repo.list_all(conn, research_status, verdict, target)
    return [PlatformStudySummary(**row) for row in rows]


def get_platform(study_id: UUID, user: CurrentUserResponse) -> PlatformStudySummary:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.get(conn, study_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plataforma não encontrada.")
    return PlatformStudySummary(**row)


def research(study_id: UUID, user: CurrentUserResponse) -> PlatformStudySummary:
    """Busca as páginas públicas e produz a leitura estruturada.

    Falha vira `research_status = 'failed'` com o motivo escrito, não exceção
    silenciosa: site que exige JavaScript ou bloqueia robô é informação sobre a
    plataforma, e o próximo passo é abrir na mão — não fingir que analisou.
    """
    require_platform_admin(user)
    with connect() as conn:
        study = repo.get(conn, study_id)
        if not study:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plataforma não encontrada.")
        repo.mark_researching(conn, study_id)

    _, test_priority = platform_study_helpers()
    bioma_features = [
        {"key": key, "label": spec["label"], "description": spec["description"]}
        for key, spec in FEATURE_CATALOG.items()
    ]

    try:
        result = platform_study_analyze_safe(
            {"url": study["url"], "targets": study["targets"], "bioma_features": bioma_features}
        )
    except Exception as exc:
        with connect() as conn:
            failed = repo.mark_failed(conn, study_id, str(exc))
        return PlatformStudySummary(**failed)

    output = result["output"]
    usage = result.get("usage") or {}
    with connect() as conn:
        saved = repo.save_research(
            conn,
            study_id,
            {
                "name": output["name"] or study["name"],
                "category": output["category"],
                "one_liner": output["one_liner"],
                "pricing_summary": output["pricing_summary"],
                "findings": {
                    "what_it_does": output["what_it_does"],
                    "who_its_for": output["who_its_for"],
                    "has_that_bioma_lacks": output["has_that_bioma_lacks"],
                    "bioma_has_that_it_lacks": output["bioma_has_that_it_lacks"],
                    "recommended_verdict": output["recommended_verdict"],
                    "verdict_reason": output["verdict_reason"],
                    "worth_hands_on_test": output["worth_hands_on_test"],
                    "open_questions": output["open_questions"],
                },
                "sources": result["sources"],
                "preview_image_url": result.get("preview_image"),
                "overlap_score": output["overlap_score"],
                "threat_level": output["threat_level"],
                "test_priority": test_priority(
                    output["overlap_score"], output["threat_level"], output["worth_hands_on_test"]
                ),
                "generation_mode": result["generation_mode"],
                "provider": result.get("provider"),
                "model": result.get("model"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "cost_cents": cost_cents(
                    result.get("model"), usage.get("input_tokens"), usage.get("output_tokens")
                ),
            },
        )
    return PlatformStudySummary(**saved)


def decide(study_id: UUID, payload: PlatformStudyVerdict, user: CurrentUserResponse) -> PlatformStudySummary:
    """O veredito é humano. A pesquisa recomenda; quem decide assina."""
    require_platform_admin(user)
    with connect() as conn:
        row = repo.set_verdict(conn, study_id, payload.verdict, payload.verdict_note, user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plataforma não encontrada.")
    return PlatformStudySummary(**row)


def remove(study_id: UUID, user: CurrentUserResponse) -> dict[str, str]:
    require_platform_admin(user)
    with connect() as conn:
        if not repo.delete(conn, study_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plataforma não encontrada.")
    return {"status": "deleted"}


def overview(user: CurrentUserResponse) -> PlatformStudyOverview:
    require_platform_admin(user)
    with connect() as conn:
        return PlatformStudyOverview(**repo.overview(conn))
