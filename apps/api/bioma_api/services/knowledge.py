"""Base de conhecimento — decisão 7, Fase 1.

Resposta do Eduardo: **"faça para ambos"** — base da EG e do cliente. Por isso
a base pende do workspace, que é o eixo que já separa os dois casos no resto do
sistema; não existe um tipo "eg" vs "cliente" aqui.

**Corte vertical, sem Fase 2-4.** Sem embeddings, sem persona, sem reranker. A
resposta declara `mode_actually_used: "lexical"` e `capabilities.dense:
"unavailable"` desde já — não por burocracia de contrato, mas para que ninguém
olhe um resultado fraco e conclua que a busca semântica está ruim quando ela
ainda não existe.

O que torna esta fase útil de verdade é a **citação verificável**: cada
fragmento guarda o offset no texto de origem, e `chunk_origin` devolve o trecho
com o que vem antes e depois. Uma base que responde sem poder mostrar de onde
tirou é pior que nenhuma — ela erra com a mesma confiança com que acerta.
"""

import hashlib
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api import chunking
from bioma_api.access import resolve_accessible_client
from bioma_api.db import connect
from bioma_api.repositories import knowledge_bases as repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.knowledge import (
    ChunkOrigin,
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    SearchHit,
    SearchResponse,
)

# Quanto de texto vizinho acompanha a citação. Suficiente para conferir que o
# trecho não foi tirado de contexto, curto o bastante para não virar o
# documento inteiro na tela.
CONTEXTO_CHARS = 400


def list_bases(workspace_id: UUID, user: CurrentUserResponse) -> list[KnowledgeBase]:
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        rows = repo.list_bases(conn, context["workspace_id"])
    return [KnowledgeBase(**row) for row in rows]


def create_base(workspace_id: UUID, payload: KnowledgeBaseCreate, user: CurrentUserResponse) -> KnowledgeBase:
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user, capability="manage_config")
        try:
            base_id = repo.create_base(
                conn,
                context["workspace_id"],
                context["tenant_organization_id"],
                payload.name.strip(),
                payload.description,
                user.id,
            )
        except Exception as erro:  # unique (workspace_id, name)
            if "knowledge_bases_workspace_id_name_key" in str(erro):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Já existe uma base com esse nome neste workspace.",
                ) from None
            raise
        row = repo.find_base(conn, base_id)
    return KnowledgeBase(**row)


def list_documents(workspace_id: UUID, base_id: UUID, user: CurrentUserResponse) -> list[KnowledgeDocument]:
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        _base_do_workspace(conn, context, base_id)
        rows = repo.list_documents(conn, base_id)
    return [KnowledgeDocument(**row) for row in rows]


def add_document(
    workspace_id: UUID, base_id: UUID, payload: KnowledgeDocumentCreate, user: CurrentUserResponse
) -> KnowledgeDocument:
    """Adiciona texto à base: grava, fragmenta e indexa numa transação só.

    Síncrono de propósito nesta fase. Fragmentar é rápido e determinístico, e
    uma fila aqui adicionaria um estado "processando" que a pessoa teria que
    ficar recarregando para ver — complexidade sem ganho enquanto não houver
    OCR ou embedding no caminho.
    """
    texto = payload.content
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user, capability="manage_work")
        _base_do_workspace(conn, context, base_id)

        document_id = repo.create_document(
            conn,
            base_id,
            {"title": payload.title.strip(), "source_kind": "text", "size_bytes": len(texto.encode("utf-8"))},
            user.id,
        )

        fragmentos = chunking.chunk_document(texto)
        if not fragmentos:
            # Documento sem nada aproveitável fica VISÍVEL com o motivo, em vez
            # de virar uma linha "indexada" com zero fragmentos que responde
            # nada e ninguém entende.
            repo.mark_failed(conn, document_id, "O texto não gerou nenhum fragmento aproveitável.")
            row = repo.find_document(conn, document_id)
            return KnowledgeDocument(**row)

        checksum = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        repo.save_version_with_chunks(conn, document_id, texto, checksum, fragmentos, user.id)
        row = repo.find_document(conn, document_id)
    return KnowledgeDocument(**row)


def list_chunks(workspace_id: UUID, document_id: UUID, user: CurrentUserResponse) -> list[KnowledgeChunk]:
    """Os fragmentos da versão corrente — a tela de inspeção.

    Poder VER como o documento foi partido é metade do valor desta fase: quando
    a base responde mal, a pergunta é sempre "o que ela leu?", e sem isto a
    resposta é um encolher de ombros.
    """
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        documento = _documento_do_workspace(conn, context, document_id)
        rows = repo.list_chunks(conn, document_id, documento["current_version"])
    return [KnowledgeChunk(**row) for row in rows]


def set_chunk_active(
    workspace_id: UUID, chunk_id: UUID, is_active: bool, user: CurrentUserResponse
) -> KnowledgeChunk:
    """Tira (ou devolve) o fragmento da busca — sem apagar.

    Apagar esconderia o motivo de a base ter respondido mal antes, que é
    justamente o que se quer entender ao desativar.
    """
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user, capability="manage_work")
        fragmento = repo.find_chunk(conn, chunk_id)
        if not fragmento or fragmento["workspace_id"] != context["workspace_id"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fragmento não encontrado.")
        repo.set_chunk_active(conn, chunk_id, is_active)
        fragmento = repo.find_chunk(conn, chunk_id)
    return KnowledgeChunk(**{k: v for k, v in fragmento.items() if k != "workspace_id"})


def search(
    workspace_id: UUID, termo: str, user: CurrentUserResponse, base_id: UUID | None = None, limit: int = 20
) -> SearchResponse:
    termo = (termo or "").strip()
    if not termo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe o que procurar.",
        )
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        if base_id:
            _base_do_workspace(conn, context, base_id)
        rows = repo.search(conn, context["workspace_id"], base_id, termo, limit)
    return SearchResponse(query=termo, hits=[SearchHit(**row) for row in rows])


def chunk_origin(workspace_id: UUID, chunk_id: UUID, user: CurrentUserResponse) -> ChunkOrigin:
    """O fragmento com o texto ao redor — a citação verificável.

    Recortado do MESMO texto de onde o fragmento saiu, pelos offsets guardados.
    É o que separa "está na página 12 deste PDF, confie em mim" de mostrar o
    trecho e o que vem antes e depois dele.
    """
    with connect() as conn:
        context = resolve_accessible_client(conn, workspace_id, user)
        fragmento = repo.find_chunk(conn, chunk_id)
        if not fragmento or fragmento["workspace_id"] != context["workspace_id"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fragmento não encontrado.")

        documento = repo.find_document(conn, fragmento["document_id"])
        texto = repo.get_version_text(conn, fragmento["document_id"], fragmento["version"])

    if texto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O texto de origem desta versão não está mais disponível.",
        )

    inicio, fim = fragmento["char_start"], fragmento["char_end"]
    return ChunkOrigin(
        chunk_id=chunk_id,
        document_id=fragmento["document_id"],
        document_title=documento["title"],
        version=fragmento["version"],
        heading_path=fragmento["heading_path"],
        char_start=inicio,
        char_end=fim,
        before=texto[max(0, inicio - CONTEXTO_CHARS):inicio],
        content=texto[inicio:fim],
        after=texto[fim:fim + CONTEXTO_CHARS],
    )


# ---------------------------------------------------------------------- interno


def _base_do_workspace(conn, context, base_id: UUID):
    base = repo.find_base(conn, base_id)
    # 404 e não 403: não se confirma a existência do que não é seu.
    if not base or base["workspace_id"] != context["workspace_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Base de conhecimento não encontrada.")
    return base


def _documento_do_workspace(conn, context, document_id: UUID):
    documento = repo.find_document(conn, document_id)
    if not documento or documento["workspace_id"] != context["workspace_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
    return documento
