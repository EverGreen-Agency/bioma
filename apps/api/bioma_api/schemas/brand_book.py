from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class BrandBookPayload(BaseModel):
    tom_de_voz: str = Field(min_length=2, max_length=500)
    arquetipo: str = Field(min_length=2, max_length=300)
    posicionamento: str | None = Field(default=None, max_length=2000)
    proposta_valor: str | None = Field(default=None, max_length=2000)
    regras_copy: list[str] = Field(default_factory=list)
    paleta_cores: list[str] = Field(default_factory=list)


class BrandBookSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    version: int
    tom_de_voz: str
    arquetipo: str
    posicionamento: str | None = None
    proposta_valor: str | None = None
    regras_copy: list[str]
    paleta_cores: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
