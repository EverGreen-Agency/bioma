from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ResearchStatus = Literal["pending", "researching", "researched", "failed"]
ThreatLevel = Literal["nenhuma", "baixa", "media", "alta", "critica"]
Verdict = Literal["assinar", "integrar", "absorver", "comprar", "monitorar", "descartar", "repensar"]
# Para qual frente a plataforma está sendo avaliada.
Target = Literal["bioma", "foton", "eg"]


class PlatformStudyCreate(BaseModel):
    url: str = Field(min_length=4, max_length=500)
    targets: list[Target] = Field(default_factory=lambda: ["bioma"])
    added_note: str | None = Field(default=None, max_length=2000)

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        """Normaliza para o dedupe por URL funcionar de verdade.

        `https://ramp.com/` e `ramp.com` são a mesma empresa; sem isso a lista
        acumularia a mesma plataforma três vezes com grafias diferentes.
        """
        clean = value.strip().rstrip("/")
        if not clean.startswith(("http://", "https://")):
            clean = f"https://{clean}"
        return clean


class PlatformStudyBulkCreate(BaseModel):
    """Colar a lista inteira de uma vez — é assim que ela chega na prática."""
    urls: list[str] = Field(min_length=1, max_length=300)
    targets: list[Target] = Field(default_factory=lambda: ["bioma"])


class PlatformStudyVerdict(BaseModel):
    verdict: Verdict
    verdict_note: str | None = Field(default=None, max_length=4000)


class PlatformStudySummary(BaseModel):
    id: UUID
    url: str
    name: str
    targets: list[str]
    added_note: str | None

    research_status: ResearchStatus
    research_error: str | None
    category: str | None
    one_liner: str | None
    pricing_summary: str | None
    findings: dict[str, Any] = Field(default_factory=dict)
    # URLs realmente buscadas. Sem elas a análise é opinião sobre um domínio.
    sources: list[str] = Field(default_factory=list)
    preview_image_url: str | None

    overlap_score: int | None
    threat_level: ThreatLevel | None
    test_priority: int | None

    verdict: Verdict | None
    verdict_note: str | None
    decided_by: UUID | None
    decided_at: datetime | None

    generation_mode: str | None
    provider: str | None
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_cents: int | None
    researched_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CriticalOverlapItem(BaseModel):
    id: UUID
    name: str
    url: str
    one_liner: str | None
    overlap_score: int | None
    threat_level: ThreatLevel | None
    verdict: Verdict | None


class PlatformStudyOverview(BaseModel):
    total: int
    pending: int
    researched: int
    failed: int
    decided: int
    # Plataformas com sobreposição alta o bastante para pesar na decisão de
    # continuar ou não construindo a parte correspondente do Bioma.
    high_threat: int
    rethink_bioma: int
    cost_cents: int
    avg_overlap: int
    critical_overlap: list[CriticalOverlapItem] = Field(default_factory=list)
