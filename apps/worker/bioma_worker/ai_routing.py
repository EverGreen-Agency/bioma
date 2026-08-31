from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


DEFAULT_WEIGHTS = {
    "quality_weight": 35,
    "quota_weight": 25,
    "cost_weight": 20,
    "reliability_weight": 10,
    "latency_weight": 10,
    "minimum_quota_headroom": Decimal("10"),
}


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _quota_headroom(row: dict[str, Any]) -> Decimal | None:
    now = datetime.now(timezone.utc)
    current: list[Decimal] = []
    for bucket in row.get("quota_buckets") or []:
        if bucket.get("confidence") == "unavailable":
            continue
        bucket_model = bucket.get("model_id")
        if bucket_model and bucket_model != row["model_id"]:
            continue
        resets_at = _as_utc(bucket.get("resets_at"))
        if resets_at and resets_at <= now:
            continue
        remaining = bucket.get("remaining_percent")
        if remaining is not None:
            current.append(Decimal(str(remaining)))
    return min(current) if current else None


def rank_candidates(job: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        eligible = True
        capability = job.get("capability") or "content"
        capabilities = set(row.get("account_capabilities") or []) | set(row.get("model_capabilities") or [])
        if capability not in capabilities:
            eligible = False
            reasons.append(f"capacidade ausente: {capability}")
        allowed_channels = row.get("allowed_channels") or []
        allowed_models = row.get("allowed_models") or []
        if allowed_channels and row["channel"] not in allowed_channels:
            eligible = False
            reasons.append("canal não permitido pela política")
        if allowed_models and row["model_id"] not in allowed_models:
            eligible = False
            reasons.append("modelo não permitido pela política")
        if row["execution_mode"] == "manual_handoff":
            eligible = False
            reasons.append("canal exige handoff manual; worker não pode executá-lo")
        headroom = _quota_headroom(row)
        minimum = Decimal(str(row.get("minimum_quota_headroom") or DEFAULT_WEIGHTS["minimum_quota_headroom"]))
        if headroom is not None and headroom < minimum:
            eligible = False
            reasons.append(f"cota abaixo da reserva ({headroom}% < {minimum}%)")
        elif headroom is None:
            reasons.append("cota externa sem medição atual")
        else:
            reasons.append(f"folga de cota: {headroom}%")
        preferred_tiers = row.get("preferred_tiers") or []
        if preferred_tiers and row["capability_tier"] in preferred_tiers:
            reasons.append(f"tier preferido: {row['capability_tier']}")
        weights = {
            key: int(row.get(key) if row.get(key) is not None else value)
            for key, value in DEFAULT_WEIGHTS.items()
            if key.endswith("_weight")
        }
        reliability = 100 if row["account_status"] == "active" else 40
        quota_score = headroom if headroom is not None else Decimal("50")
        score = (
            Decimal(row["quality_score"] * weights["quality_weight"])
            + quota_score * Decimal(weights["quota_weight"])
            + Decimal(row["cost_score"] * weights["cost_weight"])
            + Decimal(reliability * weights["reliability_weight"])
            + Decimal(row["latency_score"] * weights["latency_weight"])
        ) / Decimal("100")
        if preferred_tiers and row["capability_tier"] not in preferred_tiers:
            score -= Decimal("8")
        if row.get("role_preferred"):
            score += Decimal("12")
            reasons.append("modelo escolhido para este papel do Harness")
        ranked.append(
            {
                **row,
                "score": max(score, Decimal("0")).quantize(Decimal("0.01")),
                "quota_headroom": headroom,
                "eligible": eligible,
                "reasons": reasons,
            }
        )
    ranked.sort(key=lambda item: (item["eligible"], item["score"], -item["priority"]), reverse=True)
    return ranked
