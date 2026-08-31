from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

KnowledgeBaseStatus = Literal["active", "archived"]
DocumentStatus = Literal["pending", "indexed", "failed"]


class KnowledgeBase(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None = None
    status: KnowledgeBaseStatus
    documents_total: int = 0
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class KnowledgeDocument(BaseModel):
    id: UUID
    base_id: UUID
    title: str
    source_kind: Literal["upload", "text"]
    mime_type: str | None = None
    size_bytes: int | None = None
    status: DocumentStatus
    # Preenchido quando a extração falhou. O documento continua visível com o
    # motivo — sumir com ele faria a pessoa reenviar sem entender por quê.
    failure_reason: str | None = None
    current_version: int
    chunks_total: int
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    # Fase 1 aceita texto colado. É o caminho mais curto para a base sair do
    # zero sem depender de storage configurado.
    content: str = Field(min_length=1, max_length=2_000_000)


class KnowledgeChunk(BaseModel):
    id: UUID
    document_id: UUID
    version: int
    position: int
    content: str
    # Trilha de títulos ancestrais, do topo ao imediato.
    heading_path: list[str] = Field(default_factory=list)
    # Offsets no texto extraído — é o que abre a citação no ponto exato.
    char_start: int
    char_end: int
    is_active: bool


class ChunkToggle(BaseModel):
    is_active: bool


class SearchHit(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    base_id: UUID
    base_name: str
    version: int
    position: int
    content: str
    heading_path: list[str] = Field(default_factory=list)
    char_start: int
    char_end: int
    rank: float


class SearchCapabilities(BaseModel):
    """O que a busca REALMENTE fez.

    Declarado no contrato desde a Fase 1 (decisão 7) para que a Fase 3 entre
    sem quebrar ninguém — e, principalmente, para que ninguém olhe um resultado
    fraco e conclua que a busca semântica está ruim quando ela nem existe.
    """

    dense: Literal["unavailable", "available"] = "unavailable"
    lexical: Literal["available"] = "available"


class SearchResponse(BaseModel):
    query: str
    # Sempre `lexical` na Fase 1. É o campo que impede a leitura errada acima.
    mode_actually_used: Literal["lexical"] = "lexical"
    capabilities: SearchCapabilities = Field(default_factory=SearchCapabilities)
    hits: list[SearchHit] = Field(default_factory=list)


class ChunkOrigin(BaseModel):
    """O fragmento no contexto do texto de origem — a citação verificável.

    `before` e `after` vêm do MESMO texto de onde o fragmento saiu, recortados
    pelos offsets guardados. Sem isso, "abrir na origem" seria um scroll
    aproximado e a citação viraria um pedido de confiança.
    """

    chunk_id: UUID
    document_id: UUID
    document_title: str
    version: int
    heading_path: list[str] = Field(default_factory=list)
    char_start: int
    char_end: int
    before: str
    content: str
    after: str
