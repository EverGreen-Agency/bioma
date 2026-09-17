"""Schemas do benchmark público.

O payload público espelha exatamente o contrato consumido pelo site
(`eg/src/config/benchmark.ts`): status + segmentos agregados e anonimizados.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

PillarKey = Literal["oferta", "demanda", "conversao"]


class BenchmarkPillar(BaseModel):
    key: PillarKey
    median: float
    min: float
    max: float


class BenchmarkSegment(BaseModel):
    segment: str
    sampleSize: int
    overallMedian: float
    pillars: list[BenchmarkPillar]


class BenchmarkPayload(BaseModel):
    status: Literal["em_breve", "ao_vivo"]
    updatedAt: datetime | None = None
    segments: list[BenchmarkSegment] = []


class BenchmarkSettingsResponse(BaseModel):
    status: Literal["em_breve", "ao_vivo"]
    min_sample: int
    updated_at: datetime


class BenchmarkSettingsUpdate(BaseModel):
    status: Literal["em_breve", "ao_vivo"] | None = None
    min_sample: int | None = None
