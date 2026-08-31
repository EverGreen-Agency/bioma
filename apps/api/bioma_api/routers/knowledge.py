from uuid import UUID

from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.knowledge import (
    ChunkOrigin,
    ChunkToggle,
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    SearchResponse,
)
from bioma_api.services import knowledge as service

# Prefixo próprio, sob workspace: a base é da EG **ou** do cliente, e é o
# workspace que diz qual — foi a resposta "faça para ambos" da decisão 7.
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}/knowledge", tags=["knowledge"])


@workspace_router.get("/bases", response_model=list[KnowledgeBase])
def list_bases(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[KnowledgeBase]:
    return service.list_bases(workspace_id, user)


@workspace_router.post("/bases", response_model=KnowledgeBase, status_code=201)
def create_base(
    workspace_id: UUID,
    payload: KnowledgeBaseCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> KnowledgeBase:
    return service.create_base(workspace_id, payload, user)


@workspace_router.get("/bases/{base_id}/documents", response_model=list[KnowledgeDocument])
def list_documents(
    workspace_id: UUID,
    base_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[KnowledgeDocument]:
    return service.list_documents(workspace_id, base_id, user)


@workspace_router.post("/bases/{base_id}/documents", response_model=KnowledgeDocument, status_code=201)
def add_document(
    workspace_id: UUID,
    base_id: UUID,
    payload: KnowledgeDocumentCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> KnowledgeDocument:
    """Adiciona texto à base: grava, fragmenta e indexa de uma vez.

    Devolve 201 mesmo quando a extração não gerou fragmento: o documento existe
    e fica visível com `status: failed` e o motivo. Recusar com 4xx apagaria o
    rastro do que a pessoa tentou enviar.
    """
    return service.add_document(workspace_id, base_id, payload, user)


@workspace_router.get("/documents/{document_id}/chunks", response_model=list[KnowledgeChunk])
def list_chunks(
    workspace_id: UUID,
    document_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[KnowledgeChunk]:
    """Como o documento foi partido. Quando a base responde mal, a pergunta é
    sempre "o que ela leu?" — esta rota é a resposta."""
    return service.list_chunks(workspace_id, document_id, user)


@workspace_router.patch("/chunks/{chunk_id}", response_model=KnowledgeChunk)
def set_chunk_active(
    workspace_id: UUID,
    chunk_id: UUID,
    payload: ChunkToggle,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> KnowledgeChunk:
    """Tira o fragmento da busca sem apagar — desativar é reversível."""
    return service.set_chunk_active(workspace_id, chunk_id, payload.is_active, user)


@workspace_router.get("/chunks/{chunk_id}/origin", response_model=ChunkOrigin)
def chunk_origin(
    workspace_id: UUID,
    chunk_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ChunkOrigin:
    """O trecho com o que vem antes e depois, recortado do texto de origem."""
    return service.chunk_origin(workspace_id, chunk_id, user)


@workspace_router.get("/search", response_model=SearchResponse)
def search(
    workspace_id: UUID,
    q: str = Query(min_length=1),
    base_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> SearchResponse:
    """Busca LEXICAL (Fase 1).

    A resposta declara `mode_actually_used` e `capabilities.dense` de propósito:
    sem isso, alguém olharia um resultado fraco e concluiria que a busca
    semântica está ruim — quando ela ainda nem existe.
    """
    return service.search(workspace_id, q, user, base_id, limit)
