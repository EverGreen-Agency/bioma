from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

KitPieceStatus = Literal["active", "discontinued"]
KitDefinitionStatus = Literal["active", "discontinued"]
KitShipmentStatus = Literal["em_producao", "enviado", "entregue", "cancelado"]


class KitPieceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    supplier: str | None = Field(default=None, max_length=200)
    unit_cost_cents: int = Field(default=0, ge=0)
    stock_qty: int = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=1000)
    status: KitPieceStatus = "active"
    metadata: dict = Field(default_factory=dict)



class KitPieceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    supplier: str | None = Field(default=None, max_length=200)
    unit_cost_cents: int | None = Field(default=None, ge=0)
    stock_qty: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=1000)
    status: KitPieceStatus | None = None
    metadata: dict | None = None


class KitPieceSummary(BaseModel):
    id: UUID
    name: str
    supplier: str | None = None
    unit_cost_cents: int
    stock_qty: int
    image_url: str | None = None
    status: KitPieceStatus
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime



class KitDefinitionPieceEntry(BaseModel):
    piece_id: UUID
    quantity: int = Field(ge=1)


class KitDefinitionCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    level: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    status: KitDefinitionStatus = "active"
    pieces: list[KitDefinitionPieceEntry] = Field(default_factory=list)


class KitDefinitionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    level: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    status: KitDefinitionStatus | None = None
    pieces: list[KitDefinitionPieceEntry] | None = None


class KitDefinitionSummary(BaseModel):
    id: UUID
    name: str
    level: str
    description: str | None = None
    status: KitDefinitionStatus
    pieces: list[KitDefinitionPieceEntry] = Field(default_factory=list)
    total_cost_cents: int = 0
    created_at: datetime
    updated_at: datetime


class KitShipmentCreateRequest(BaseModel):
    kit_definition_id: UUID
    client_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class KitShipmentStatusUpdateRequest(BaseModel):
    status: KitShipmentStatus
    notes: str | None = Field(default=None, max_length=2000)


class KitShipmentSummary(BaseModel):
    id: UUID
    kit_definition_id: UUID
    kit_name: str
    client_id: UUID
    client_name: str
    status: KitShipmentStatus
    notes: str | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
