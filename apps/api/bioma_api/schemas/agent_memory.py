from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MemoryCategory = Literal["identity", "fact", "preference", "directive"]
SkillStatus = Literal["pending_review", "approved", "rejected", "retired"]


class AgentMemory(BaseModel):
    id: UUID
    workspace_id: UUID | None
    category: MemoryCategory
    title: str
    body: str
    authored_by: UUID | None
    # Nulo = compartilhada (fato/diretriz/identidade, visível a todos).
    # Preenchido = preferência pessoal de quem é o dono — só entra no dossiê
    # dele. Só pode ser não-nulo quando category = "preference".
    owner_user_id: UUID | None
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime


class AgentMemoryOwnerUpdate(BaseModel):
    """Corrige a classificação pessoal x compartilhada de uma preferência."""
    is_personal: bool
    reason: str = Field(min_length=1, max_length=500)


class AgentMemoryCreate(BaseModel):
    workspace_id: UUID | None = None
    category: MemoryCategory
    title: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    reason: str = Field(min_length=1, max_length=500)


class AgentMemoryUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    reason: str = Field(min_length=1, max_length=500)


class AgentMemoryStatusUpdate(BaseModel):
    status: Literal["active", "archived"]
    reason: str = Field(min_length=1, max_length=500)


class AgentMemoryRevision(BaseModel):
    id: UUID
    memory_id: UUID
    action: Literal["created", "updated", "archived", "restored"]
    previous_body: str | None
    new_body: str | None
    actor_user_id: UUID | None
    reason: str
    created_at: datetime


class AgentSkill(BaseModel):
    id: UUID
    workspace_id: UUID | None
    name: str
    description: str
    procedure: str
    status: SkillStatus
    proposed_by: UUID | None
    source_context: str | None
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    use_count: int
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentSkillReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=500)
