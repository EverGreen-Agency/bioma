"""Acervo de cases da EG — leitura pública para o site, escrita pela EG.

- `public_router` (`/public/cases`): SEM autenticação. Serve **apenas** casos com
  `status = 'published'`, o que por definição de banco (migração 0103) exclui
  qualquer caso que exponha cliente nomeado sem autorização registrada.
- `admin_router` (`/cases`): leitura completa, inclusive os retidos, com o motivo.

Mesmo desenho do `benchmark`: o Bioma é a fonte, o site lê. O site mantém os
arrays TypeScript como fallback — uma apresentação comercial não pode ficar em
branco porque a API estava reiniciando.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from bioma_api.auth import current_user_from_request
from bioma_api.db import connect
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.access import require_platform_admin

public_router = APIRouter(prefix="/public/cases", tags=["cases-public"])
admin_router = APIRouter(prefix="/cases", tags=["cases-admin"])

Deck = Literal["growth", "tech"]
Lang = Literal["pt", "en"]

_SELECT = """
    select c.slug, c.deck, c.display_order,
           t.name, t.category, t.headline, t.metric, t.evidence,
           t.highlights, t.sections
      from eg_cases c
      join eg_case_translations t on t.case_id = c.id
     where t.lang = %s
       and (%s is null or c.deck = %s or c.deck = 'ambos')
"""


def _rows_to_cases(rows) -> list[dict]:
    return [
        {
            "id": row[0],
            "deck": row[1],
            "name": row[3],
            "category": row[4],
            "headline": row[5],
            "metric": row[6],
            "evidence": row[7],
            "highlights": row[8],
            "sections": row[9],
        }
        for row in rows
    ]


@public_router.get("")
def list_public_cases(
    deck: Deck | None = Query(default=None, description="growth ou tech; omitido traz os dois"),
    lang: Lang = Query(default="pt"),
) -> dict:
    """O formato do item é o mesmo `CaseStudy` que o site já consome."""
    with connect() as conn:
        rows = conn.execute(
            _SELECT + " and c.status = 'published' order by c.deck, c.display_order",
            (lang, deck, deck),
        ).fetchall()
    return {"cases": _rows_to_cases(rows)}


@admin_router.get("")
def list_all_cases(
    lang: Lang = Query(default="pt"),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict:
    """Inclui os retidos, com o porquê — é esta tela que mostra o que falta assinar."""
    require_platform_admin(user)
    with connect() as conn:
        rows = conn.execute(
            """
            select c.slug, c.deck, c.display_order, c.status,
                   c.client_named, c.consent_status, c.consent_note, c.consent_at,
                   t.name, t.headline
              from eg_cases c
              left join eg_case_translations t on t.case_id = c.id and t.lang = %s
             order by c.status, c.deck, c.display_order
            """,
            (lang,),
        ).fetchall()
    return {
        "cases": [
            {
                "id": r[0],
                "deck": r[1],
                "status": r[3],
                "client_named": r[4],
                "consent_status": r[5],
                "consent_note": r[6],
                "consent_at": r[7],
                "name": r[8],
                "headline": r[9],
                "blocked_reason": (
                    "cliente nomeado sem autorização registrada"
                    if r[4] and r[5] not in ("granted", "waived", "not_applicable")
                    else None
                ),
            }
            for r in rows
        ]
    }


@admin_router.patch("/{deck}/{slug}/consent")
def register_consent(
    deck: Deck,
    slug: str,
    consent_status: Literal["none", "requested", "granted", "waived", "not_applicable"],
    consent_note: str | None = None,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> dict:
    """Registrar a autorização é o que destrava a publicação.

    Não publica sozinho: muda o estado de autorização e deixa o caso elegível.
    Publicar segue sendo um ato deliberado.
    """
    require_platform_admin(user)
    with connect() as conn:
        row = conn.execute(
            """
            update eg_cases
               set consent_status = %s,
                   consent_note = coalesce(%s, consent_note),
                   consent_at = case when %s in ('granted', 'waived') then now() else null end,
                   seeded = false,
                   updated_at = now()
             where deck = %s and slug = %s
            returning slug, consent_status, status
            """,
            (consent_status, consent_note, consent_status, deck, slug),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="case não encontrado")
    return {"id": row[0], "consent_status": row[1], "status": row[2]}
