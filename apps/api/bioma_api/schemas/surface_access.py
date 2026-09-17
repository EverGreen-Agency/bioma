from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

SurfaceEffect = Literal["allow", "deny"]
SurfaceReason = Literal[
    "locked",
    "platform_admin",
    "not_contracted",
    "maturity",
    "team_denied",
    "team_allowed",
    "user_denied",
    "user_allowed",
    "preference",
    "default",
]


class SurfaceAccessEntry(BaseModel):
    """Decisão sobre uma tela, com o porquê junto.

    `allowed` e `visible` são coisas diferentes de propósito: a tela some do
    menu por preferência sem deixar de responder pela URL. Quem consome precisa
    escolher qual dos dois olhar — menu usa `visible`, guarda de rota usa
    `allowed`.
    """

    surface_key: str
    label: str
    group: str
    parent: str | None = None
    locked: bool
    allowed: bool
    visible: bool
    can_prefer: bool
    reason: SurfaceReason
    # Frase pronta para a tela. Vem do mesmo cálculo que decidiu — explicação
    # derivada em outro lugar acabaria contradizendo a decisão.
    detail: str
    sources: list[str] = Field(default_factory=list)


class SurfacePreferenceUpdate(BaseModel):
    surface_key: str = Field(min_length=2, max_length=120)
    hidden: bool


class SurfaceGrantEntry(BaseModel):
    id: UUID
    surface_key: str
    label: str
    group: str
    team_id: UUID | None = None
    user_id: UUID | None = None
    effect: SurfaceEffect
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class SurfaceGrantUpsert(BaseModel):
    surface_key: str = Field(min_length=2, max_length=120)
    effect: SurfaceEffect
    note: str | None = Field(default=None, max_length=500)


class SurfaceCatalogEntry(BaseModel):
    """O catálogo em si — a tela de admin precisa saber o que existe para poder
    conceder ou negar. Sem isto, o admin digitaria chaves na mão."""

    surface_key: str
    label: str
    group: str
    parent: str | None = None
    scope: Literal["eg", "client", "both"]
    locked: bool
    module: str | None = None
    feature_key: str | None = None
