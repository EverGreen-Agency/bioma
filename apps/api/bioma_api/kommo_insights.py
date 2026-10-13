"""Leitura analítica do Kommo: do lead bruto da API ao painel de dados reais.

Tudo aqui é função pura (sem banco, sem rede) para ser testável: o serviço
`kommo_crm` busca os leads, compacta com `compact_lead` e guarda; o painel é
montado por `build_dashboard` a cada leitura, para qualquer período.

`compact_lead` descarta de propósito todo dado pessoal. O snapshot guarda só o
que o painel agrega: datas, etapa, valor e campos de classificação.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from datetime import datetime, timezone
from typing import Any

WON_STATUS_ID = 142
LOST_STATUS_ID = 143

# (chave, rótulo no painel, nomes aceitos do campo personalizado no Kommo).
# O casamento é por nome normalizado porque o id do campo muda de conta para conta.
DIMENSIONS: list[tuple[str, str, tuple[str, ...]]] = [
    ("origem", "Origem do lead", ("origem do lead", "origem")),
    ("segmento", "Segmento", ("segmento",)),
    ("produto", "Produto de interesse", ("produto de interesse", "produto")),
    ("solicitacao", "Solicitação inicial", ("solicitacao inicial",)),
    ("tipo_atendimento", "Tipo de atendimento", ("tipo de atendimento",)),
    ("uf", "Estado (UF)", ("uf", "estado")),
    ("representante", "Região ou representante", ("regiao/representante indicado", "representante")),
    ("status_representante", "Status do representante", ("status representante",)),
    ("motivo_perda", "Motivo de perda", ("motivo de perda",)),
]

_VISIT_FIELDS = ("data da visita/agendamento", "data da visita")
_UTM_FIELDS = {"utm_source": "source", "utm_medium": "medium", "utm_campaign": "campaign"}
_TIMELINE_BUCKETS = 12


def normalize(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip().lower()


_FIELD_TO_DIMENSION = {name: key for key, _label, names in DIMENSIONS for name in names}


def compact_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """Reduz um lead da API v4 ao que o painel agrega, sem dado pessoal."""
    dims: dict[str, list[str]] = {}
    utm: dict[str, str] = {}
    has_visit = False

    for entry in lead.get("custom_fields_values") or []:
        name = normalize(entry.get("field_name"))
        values = [str(v.get("value")).strip() for v in entry.get("values") or [] if v.get("value") not in (None, "")]
        if not values:
            continue
        if name in _FIELD_TO_DIMENSION:
            dims.setdefault(_FIELD_TO_DIMENSION[name], []).extend(values)
        elif name in _VISIT_FIELDS:
            has_visit = True
        elif name in _UTM_FIELDS:
            utm[_UTM_FIELDS[name]] = values[0]

    loss_reasons = (lead.get("_embedded") or {}).get("loss_reason") or []
    return {
        "id": lead.get("id"),
        "created_at": lead.get("created_at") or 0,
        "updated_at": lead.get("updated_at") or 0,
        "closed_at": lead.get("closed_at") or None,
        "pipeline_id": lead.get("pipeline_id"),
        "status_id": lead.get("status_id"),
        "price": lead.get("price") or 0,
        "loss_reason": (loss_reasons[0].get("name") if loss_reasons else None),
        "dims": dims,
        "has_visit": has_visit,
        "utm": utm,
    }


def compact_pipelines(pipelines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for pipeline in pipelines:
        statuses = (pipeline.get("_embedded") or {}).get("statuses") or []
        result.append(
            {
                "id": pipeline.get("id"),
                "name": pipeline.get("name") or "Funil",
                "is_main": bool(pipeline.get("is_main")),
                "statuses": [
                    {"id": s.get("id"), "name": s.get("name") or "", "sort": s.get("sort") or 0}
                    for s in sorted(statuses, key=lambda item: item.get("sort") or 0)
                ],
            }
        )
    return result


def _stage_kind(status_id: Any) -> str:
    if status_id == WON_STATUS_ID:
        return "won"
    if status_id == LOST_STATUS_ID:
        return "lost"
    return "open"


def _ranked(counter: Counter, total: int) -> list[dict[str, Any]]:
    return [
        {"label": label, "count": count, "share": (count / total if total else 0.0)}
        for label, count in counter.most_common()
    ]


def _day_label(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d/%m")


def build_dashboard(
    leads: list[dict[str, Any]],
    pipelines: list[dict[str, Any]],
    days: int,
    now_ts: float,
) -> dict[str, Any]:
    """Monta o painel para os leads criados nos últimos `days` dias (0 = todo o histórico)."""
    window_start = now_ts - days * 86400 if days > 0 else 0
    previous_start = window_start - days * 86400 if days > 0 else 0
    scoped = [lead for lead in leads if lead["created_at"] >= window_start]
    previous = (
        [lead for lead in leads if previous_start <= lead["created_at"] < window_start] if days > 0 else []
    )
    total = len(scoped)

    won = [lead for lead in scoped if lead["status_id"] == WON_STATUS_ID]
    lost = [lead for lead in scoped if lead["status_id"] == LOST_STATUS_ID]

    # Funis: etapa em que cada lead do recorte está AGORA (foto atual, não histórico de passagem).
    stage_counts = Counter((lead["pipeline_id"], lead["status_id"]) for lead in scoped)
    pipeline_rows = []
    for pipeline in pipelines:
        stages = [
            {
                "id": status["id"],
                "name": status["name"],
                "kind": _stage_kind(status["id"]),
                "count": stage_counts.get((pipeline["id"], status["id"]), 0),
            }
            for status in pipeline["statuses"]
        ]
        pipeline_total = sum(stage["count"] for stage in stages)
        if pipeline_total or pipeline.get("is_main"):
            pipeline_rows.append(
                {"id": pipeline["id"], "name": pipeline["name"], "leads": pipeline_total, "stages": stages}
            )
    pipeline_rows.sort(key=lambda row: -row["leads"])

    # Linha do tempo em intervalos iguais, do início do recorte até agora.
    timeline: list[dict[str, Any]] = []
    if scoped:
        start = window_start if days > 0 else min(lead["created_at"] for lead in scoped)
        span = max(now_ts - start, 86400.0)
        size = span / _TIMELINE_BUCKETS
        counts = [0] * _TIMELINE_BUCKETS
        for lead in scoped:
            index = min(_TIMELINE_BUCKETS - 1, int((lead["created_at"] - start) / size))
            counts[index] += 1
        timeline = [
            {
                "label": _day_label(start + i * size),
                "range_label": f"{_day_label(start + i * size)} a {_day_label(start + (i + 1) * size - 1)}",
                "leads": counts[i],
            }
            for i in range(_TIMELINE_BUCKETS)
        ]

    dimensions = []
    quality = []
    for key, label, _names in DIMENSIONS:
        counter: Counter = Counter()
        filled = 0
        for lead in scoped:
            values = lead["dims"].get(key) or []
            if values:
                filled += 1
                counter.update(values)
        dimensions.append({"key": key, "label": label, "filled": filled, "total": total, "items": _ranked(counter, filled)})
        quality.append({"key": key, "label": label, "filled": filled, "total": total})

    extra_quality = [
        ("valor", "Valor do negócio", sum(1 for lead in scoped if lead["price"] > 0)),
        ("utm", "UTM de origem (rastreamento)", sum(1 for lead in scoped if lead["utm"].get("source"))),
        ("visita", "Data de visita ou agendamento", sum(1 for lead in scoped if lead["has_visit"])),
    ]
    quality.extend({"key": key, "label": label, "filled": filled, "total": total} for key, label, filled in extra_quality)
    quality.sort(key=lambda row: -row["filled"])

    loss_counter = Counter(lead["loss_reason"] for lead in lost if lead["loss_reason"])
    utm_counter = Counter(lead["utm"]["campaign"] for lead in scoped if lead["utm"].get("campaign"))

    return {
        "period_days": days,
        "totals": {
            "leads_all_time": len(leads),
            "leads": total,
            "leads_previous": len(previous) if days > 0 else None,
            "open": total - len(won) - len(lost),
            "won": len(won),
            "lost": len(lost),
            "won_value": float(sum(lead["price"] for lead in won)),
            "open_value": float(
                sum(lead["price"] for lead in scoped if _stage_kind(lead["status_id"]) == "open")
            ),
            "with_visit": sum(1 for lead in scoped if lead["has_visit"]),
            "last_lead_at": max((lead["created_at"] for lead in leads), default=None),
            "last_activity_at": max((lead["updated_at"] for lead in leads), default=None),
        },
        "pipelines": pipeline_rows,
        "timeline": timeline,
        "dimensions": dimensions,
        "quality": quality,
        "loss_reasons": _ranked(loss_counter, sum(loss_counter.values())),
        "campaigns": _ranked(utm_counter, sum(utm_counter.values()))[:10],
    }
