from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BriefingDiagnosisItem(BaseModel):
    observation: str
    evidence: str


class BriefingFocusItem(BaseModel):
    focus: str
    rationale: str
    service: str


class BriefingDraft(BaseModel):
    summary: str
    diagnosis: list[BriefingDiagnosisItem] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    recommended_focus: list[BriefingFocusItem] = Field(default_factory=list)
    questions_for_client: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)


class BriefingDraftResponse(BaseModel):
    client_name: str
    generation_mode: Literal["live", "preview"]
    # Rastreabilidade da honestidade: quais fontes tinham dado real e quais não.
    sources_used: list[str] = Field(default_factory=list)
    missing_sources: list[str] = Field(default_factory=list)
    draft: BriefingDraft
    artifact_id: UUID | None = None
