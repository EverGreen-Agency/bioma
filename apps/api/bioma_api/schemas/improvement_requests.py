from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ImprovementRequest(BaseModel):
    id: UUID
    workspace_id: UUID | None
    title: str
    need: str
    evidence: str | None
    # Decide onde a tarefa nasce ao converter: entrega do cliente vai visível no
    # board dele; melhoria interna nasce escondida.
    client_deliverable: bool
    status: Literal["pending", "converted", "rejected"]
    proposed_by: UUID | None
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    task_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ImprovementRequestCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    need: str = Field(min_length=2, max_length=4000)
    evidence: str | None = Field(default=None, max_length=4000)
    workspace_id: UUID | None = None
    client_deliverable: bool = False


class ImprovementRequestConvert(BaseModel):
    """Converte em tarefa. `list_id` decide a frente (Tech, Growth, Social)."""
    list_id: UUID
    review_note: str | None = Field(default=None, max_length=500)
    due_date: datetime | None = None
    owner_id: UUID | None = None


class ImprovementRequestReject(BaseModel):
    review_note: str | None = Field(default=None, max_length=500)
