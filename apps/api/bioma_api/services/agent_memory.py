"""Memória persistente dos agentes — CRUD com auditoria e revisão de skills.

Toda esta API é EG-only (mesma regra do copiloto). Memória de workspace é sobre
o CLIENTE, não do cliente: quem lê/edita é o time EG, nunca o usuário do
cliente — está fora de `ClientModuleBoundary`, não é um módulo habilitável.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import agent_memory as repo
from bioma_api.repositories import workspaces as workspaces_repo
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


def list_memories(
    workspace_id: UUID | None, include_global: bool, user: CurrentUserResponse
) -> list[AgentMemory]:
    require_platform_admin(user)
    with connect() as conn:
        if workspace_id:
            _require_workspace(conn, workspace_id, user)
        rows = repo.list_memories(conn, workspace_id, include_global)
    return [AgentMemory(**row) for row in rows]


def create_memory(payload: AgentMemoryCreate, user: CurrentUserResponse) -> AgentMemory:
    require_platform_admin(user)
    with connect() as conn:
        if payload.workspace_id:
            _require_workspace(conn, payload.workspace_id, user)
        row = repo.create_memory(
            conn,
            payload.workspace_id,
            payload.category,
            payload.title,
            payload.body,
            user.id,
            payload.reason,
            # Preferência escrita à mão é sempre de quem escreveu — não existe
            # "prefiro X" em nome de outra pessoa. `create_memory` já ignora
            # isto se a categoria não for `preference`.
            owner_user_id=user.id,
        )
    return AgentMemory(**row)


def set_memory_owner(memory_id: UUID, payload: AgentMemoryOwnerUpdate, user: CurrentUserResponse) -> AgentMemory:
    """Corrige "isto é meu/da EG" — o agente vai classificar errado às vezes."""
    require_platform_admin(user)
    with connect() as conn:
        current = repo.get_memory(conn, memory_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memória não encontrada.")
        if current["workspace_id"]:
            _require_workspace(conn, current["workspace_id"], user)
        try:
            row = repo.set_memory_owner(
                conn,
                memory_id,
                user.id if payload.is_personal else None,
                user.id,
                payload.reason,
            )
        except repo.NotPreferenceError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        assert row is not None
    return AgentMemory(**row)


def update_memory(memory_id: UUID, payload: AgentMemoryUpdate, user: CurrentUserResponse) -> AgentMemory:
    require_platform_admin(user)
    with connect() as conn:
        current = repo.get_memory(conn, memory_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memória não encontrada.")
        if current["workspace_id"]:
            _require_workspace(conn, current["workspace_id"], user)
        row = repo.update_memory_body(conn, memory_id, payload.body, user.id, payload.reason)
        assert row is not None  # existência já confirmada acima, dentro da mesma conexão
    return AgentMemory(**row)


def set_memory_status(memory_id: UUID, payload: AgentMemoryStatusUpdate, user: CurrentUserResponse) -> AgentMemory:
    require_platform_admin(user)
    with connect() as conn:
        current = repo.get_memory(conn, memory_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memória não encontrada.")
        if current["workspace_id"]:
            _require_workspace(conn, current["workspace_id"], user)
        row = repo.set_memory_status(conn, memory_id, payload.status, user.id, payload.reason)
        assert row is not None  # existência já confirmada acima, dentro da mesma conexão
    return AgentMemory(**row)


def list_memory_revisions(memory_id: UUID, user: CurrentUserResponse) -> list[AgentMemoryRevision]:
    require_platform_admin(user)
    with connect() as conn:
        current = repo.get_memory(conn, memory_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memória não encontrada.")
        if current["workspace_id"]:
            _require_workspace(conn, current["workspace_id"], user)
        rows = repo.list_memory_revisions(conn, memory_id)
    return [AgentMemoryRevision(**row) for row in rows]


def list_skills(
    workspace_id: UUID | None, include_global: bool, review_status: str | None, user: CurrentUserResponse
) -> list[AgentSkill]:
    require_platform_admin(user)
    with connect() as conn:
        if workspace_id:
            _require_workspace(conn, workspace_id, user)
        rows = repo.list_skills(conn, workspace_id, include_global, review_status)
    return [AgentSkill(**row) for row in rows]


def review_skill(skill_id: UUID, payload: AgentSkillReview, user: CurrentUserResponse) -> AgentSkill:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.review_skill(conn, skill_id, payload.status, user.id, payload.review_note)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Skill não encontrada ou já revisada (só dá pra revisar uma vez).",
            )
    return AgentSkill(**row)


def retire_skill(skill_id: UUID, user: CurrentUserResponse) -> AgentSkill:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.retire_skill(conn, skill_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill aprovada não encontrada.")
    return AgentSkill(**row)


def _require_workspace(conn, workspace_id: UUID, user: CurrentUserResponse) -> None:
    # Chamado só depois de require_platform_admin, então is_admin=True aqui é
    # sempre correto — a checagem que resta é "esse workspace existe mesmo".
    client = workspaces_repo.find_accessible_client(conn, workspace_id, True, user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
