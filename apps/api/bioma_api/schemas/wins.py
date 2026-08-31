from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

WinCategory = Literal["comercial", "operacao", "produto", "cliente", "time", "financeiro"]
WinVisibility = Literal["eg", "client"]


class WinCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: WinCategory = "operacao"
    metric_value: Decimal | None = None
    metric_unit: str | None = Field(default=None, max_length=30)
    workspace_id: UUID | None = None
    # Vitória do CEO: é o recorte que vai para o Fóton.
    is_ceo: bool = False
    credited_user_ids: list[UUID] = Field(default_factory=list, max_length=20)
    # `client` só aparece no hub do cliente se alguém liberar de propósito.
    visibility: WinVisibility = "eg"
    occurred_at: datetime | None = None


class WinUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: WinCategory | None = None
    visibility: WinVisibility | None = None
    pinned: bool | None = None
    is_ceo: bool | None = None
    occurred_at: datetime | None = None


class WinReaction(BaseModel):
    emoji: str = Field(min_length=1, max_length=8)


class WinSummary(BaseModel):
    id: UUID
    title: str
    description: str | None
    category: WinCategory
    # `automatic` = detectada no banco; `manual` = alguém digitou.
    source: Literal["manual", "automatic"]
    rule_key: str | None
    # Qual linha disparou. Vitória automática sem evidência é indistinguível de
    # vitória inventada.
    evidence: dict[str, Any] = Field(default_factory=dict)
    metric_value: Decimal | None
    metric_unit: str | None
    benchmark_link: dict[str, Any] | None
    workspace_id: UUID | None
    is_ceo: bool
    credited_user_ids: list[UUID] = Field(default_factory=list)
    visibility: WinVisibility
    pinned: bool
    # {emoji: [user_id]} — a contagem é derivada de quem reagiu, não um inteiro.
    reactions: dict[str, list[str]] = Field(default_factory=dict)
    occurred_at: datetime
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class WinDetectionResult(BaseModel):
    """Resultado de uma varredura dos detectores."""
    scanned_rules: int
    created: int
    skipped_duplicates: int
    by_rule: dict[str, int] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


class WinOverview(BaseModel):
    total: int
    automatic: int
    manual: int
    ceo: int
    last_7_days: int
    by_category: list[dict[str, Any]] = Field(default_factory=list)
