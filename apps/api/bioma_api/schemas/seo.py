from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SeoCollectRequest(BaseModel):
    target: str = Field(default="evergreenmkt.com.br", min_length=3, max_length=253)

    @field_validator("target")
    @classmethod
    def normalize_target(cls, value: str) -> str:
        target = value.strip().lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").strip("/")
        if "/" in target or " " in target or "." not in target:
            raise ValueError("Informe apenas o domínio, sem caminho.")
        return target


class SeoSnapshotSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    source: str
    source_endpoint: str
    source_task_id: str | None
    target: str
    location_code: int
    language_code: str
    has_data: bool
    organic: dict[str, Any]
    paid: dict[str, Any]
    cost_usd: Decimal | None
    measured_at: datetime
    created_at: datetime


class SeoSnapshotState(BaseModel):
    available: bool
    latest: SeoSnapshotSummary | None = None
