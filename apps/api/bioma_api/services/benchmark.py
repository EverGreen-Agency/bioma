"""Agregação e anonimização do benchmark público.

Regras de anonimização (garantidas aqui, no backend):
- só entram organizações com `benchmark_consent = true` e `benchmark_segment` definido;
- usa a avaliação de Raio-X mais recente de cada organização;
- só publica um segmento com `count(distinct organização) >= min_sample` (k-anonimato);
- nunca retorna dado de cliente individual — apenas mediana/mín/máx por pilar.

Enquanto o toggle estiver em `em_breve` (ou não houver segmento com base
suficiente), o payload volta vazio e o site mostra o estado "Em Breve".
"""

from datetime import datetime, timezone

from bioma_api.db import connect
from bioma_api.schemas.benchmark import (
    BenchmarkPayload,
    BenchmarkPillar,
    BenchmarkSegment,
    BenchmarkSettingsResponse,
    BenchmarkSettingsUpdate,
)

_PILLAR_ORDER = {"oferta": 0, "demanda": 1, "conversao": 2}

_AGGREGATE_SQL = """
with latest as (
  select distinct on (organization_id, pillar)
    organization_id, pillar, score
  from raio_x_scores
  order by organization_id, pillar, assessed_at desc
),
consented as (
  select o.id as org_id, o.benchmark_segment as segment, l.pillar, l.score
  from organizations o
  join latest l on l.organization_id = o.id
  where o.benchmark_consent = true
    and o.benchmark_segment is not null
    and o.benchmark_segment <> ''
),
seg_counts as (
  select segment, count(distinct org_id)::int as n
  from consented
  group by segment
)
select
  c.segment,
  c.pillar,
  sc.n as sample_size,
  percentile_cont(0.5) within group (order by c.score)::float as median,
  min(c.score)::float as min_score,
  max(c.score)::float as max_score
from consented c
join seg_counts sc on sc.segment = c.segment
where sc.n >= %(min_sample)s
group by c.segment, c.pillar, sc.n
order by c.segment, c.pillar
"""


def get_settings_row() -> dict:
    with connect() as conn:
        row = conn.execute(
            "select status, min_sample, updated_at from benchmark_settings where id = true"
        ).fetchone()
    # Fallback defensivo caso a linha singleton não exista.
    return row or {"status": "em_breve", "min_sample": 5, "updated_at": datetime.now(timezone.utc)}


def get_public_benchmark() -> BenchmarkPayload:
    settings = get_settings_row()

    if settings["status"] != "ao_vivo":
        return BenchmarkPayload(status="em_breve", segments=[])

    with connect() as conn:
        rows = conn.execute(_AGGREGATE_SQL, {"min_sample": settings["min_sample"]}).fetchall()

    # Agrupa linhas (segmento, pilar) em segmentos.
    by_segment: dict[str, dict] = {}
    for row in rows:
        seg = by_segment.setdefault(
            row["segment"],
            {"segment": row["segment"], "sampleSize": row["sample_size"], "pillars": []},
        )
        seg["pillars"].append(
            BenchmarkPillar(
                key=row["pillar"],
                median=round(row["median"], 1),
                min=round(row["min_score"], 1),
                max=round(row["max_score"], 1),
            )
        )

    segments: list[BenchmarkSegment] = []
    for seg in by_segment.values():
        pillars = sorted(seg["pillars"], key=lambda p: _PILLAR_ORDER.get(p.key, 99))
        # Raio-X geral = média dos três pilares (Documento-Mestre §9).
        overall = round(sum(p.median for p in pillars) / len(pillars), 1) if pillars else 0.0
        segments.append(
            BenchmarkSegment(
                segment=seg["segment"],
                sampleSize=seg["sampleSize"],
                overallMedian=overall,
                pillars=pillars,
            )
        )

    segments.sort(key=lambda s: s.segment)

    if not segments:
        # Toggle ao_vivo mas nenhum segmento passou o k-anonimato ainda.
        return BenchmarkPayload(status="em_breve", segments=[])

    return BenchmarkPayload(
        status="ao_vivo",
        updatedAt=settings["updated_at"],
        segments=segments,
    )


def get_settings_response() -> BenchmarkSettingsResponse:
    return BenchmarkSettingsResponse(**get_settings_row())


def update_settings(payload: BenchmarkSettingsUpdate) -> BenchmarkSettingsResponse:
    fields: list[str] = []
    params: dict = {}
    if payload.status is not None:
        fields.append("status = %(status)s")
        params["status"] = payload.status
    if payload.min_sample is not None:
        fields.append("min_sample = %(min_sample)s")
        params["min_sample"] = payload.min_sample

    if fields:
        fields.append("updated_at = now()")
        with connect() as conn:
            conn.execute(
                f"update benchmark_settings set {', '.join(fields)} where id = true",
                params,
            )

    return get_settings_response()
