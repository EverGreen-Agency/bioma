from uuid import UUID

from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.agent_memory import (
    AgentMemory,
    AgentMemoryCreate,
    AgentMemoryOwnerUpdate,
    AgentMemoryRevision,
    AgentMemoryStatusUpdate,
    AgentMemoryUpdate,
    AgentSkill,
    AgentSkillReview,
)
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services import agent_memory as service

router = APIRouter(prefix="/agent-memory", tags=["agent-memory"])


@router.get("/memories", response_model=list[AgentMemory])
def list_memories(
    workspace_id: UUID | None = Query(default=None),
    include_global: bool = Query(default=True),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[AgentMemory]:
    return service.list_memories(workspace_id, include_global, user)


@router.post("/memories", response_model=AgentMemory, status_code=201)
def create_memory(
    payload: AgentMemoryCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AgentMemory:
    return service.create_memory(payload, user)


@router.patch("/memories/{memory_id}", response_model=AgentMemory)
def update_memory(
    memory_id: UUID,
    payload: AgentMemoryUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AgentMemory:
    return service.update_memory(memory_id, payload, user)


@router.patch("/memories/{memory_id}/status", response_model=AgentMemory)
def set_memory_status(
    memory_id: UUID,
    payload: AgentMemoryStatusUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AgentMemory:
    return service.set_memory_status(memory_id, payload, user)


@router.patch("/memories/{memory_id}/owner", response_model=AgentMemory)
def set_memory_owner(
    memory_id: UUID,
    payload: AgentMemoryOwnerUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AgentMemory:
    """Corrige classificação pessoal x compartilhada — só vale para 'preference'."""
    return service.set_memory_owner(memory_id, payload, user)


@router.get("/memories/{memory_id}/revisions", response_model=list[AgentMemoryRevision])
def list_memory_revisions(
    memory_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[AgentMemoryRevision]:
    """O que mudou, quando, por quem (ou pelo agente) e por quê."""
    return service.list_memory_revisions(memory_id, user)


@router.get("/skills", response_model=list[AgentSkill])
def list_skills(
    workspace_id: UUID | None = Query(default=None),
    include_global: bool = Query(default=True),
    review_status: str | None = Query(default=None, alias="status"),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[AgentSkill]:
    return service.list_skills(workspace_id, include_global, review_status, user)


@router.post("/skills/{skill_id}/review", response_model=AgentSkill)
def review_skill(
    skill_id: UUID,
    payload: AgentSkillReview,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AgentSkill:
    """Skill proposta pelo copiloto só entra em uso depois desta aprovação."""
    return service.review_skill(skill_id, payload, user)


@router.post("/skills/{skill_id}/retire", response_model=AgentSkill)
def retire_skill(
    skill_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> AgentSkill:
    return service.retire_skill(skill_id, user)
