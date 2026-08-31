from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

FeatureState = Literal["hidden", "coming_soon", "beta", "active"]


class FeatureFlag(BaseModel):
    """Estado efetivo de uma feature para uma organização.

    `is_override` distingue "alguém decidiu isso para este cliente" de "está
    valendo o default do catálogo" — sem isso não dá para saber se um estado é
    intencional ou herdado.
    """
    feature_key: str
    label: str
    description: str
    state: FeatureState
    is_override: bool
    accessible: bool
    note: str | None = None
    updated_at: datetime | None = None


class FeatureFlagUpsert(BaseModel):
    feature_key: str = Field(min_length=2, max_length=80)
    state: FeatureState
    note: str | None = Field(default=None, max_length=500)
