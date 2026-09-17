"""Bases de conhecimento, documentos e fragmentos — decisão 7, Fase 1.

Nome `knowledge_bases` e não `knowledge`: `repositories/knowledge.py` já era
do conteúdo SEEDADO (Banco de Ideias, Stack, wiki), que é outra coisa. Eu
sobrescrevi aquele arquivo por engano ao criar este, e oito smokes caíram —
o nome separado existe para isso não se repetir.
"""

from typing import Any
from uuid import UUID

BASE_COLUMNS = """
  b.id, b.tenant_organization_id, b.workspace_id, b.name, b.description,
  b.status, b.created_at, b.updated_at
"""

DOC_COLUMNS = """
  d.id, d.base_id, d.title, d.source_kind, d.storage_key, d.mime_type,
  d.size_bytes, d.status, d.failure_reason, d.current_version, d.chunks_total,
  d.created_at, d.updated_at
"""


def list_bases(conn, workspace_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        f"""
        select {BASE_COLUMNS},
          (select count(*) from knowledge_documents d where d.base_id = b.id)::int as documents_total
        from knowledge_bases b
        where b.workspace_id = %s
        order by b.status asc, b.name asc
        """,
        (workspace_id,),
    ).fetchall()


def find_base(conn, base_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"""
        select {BASE_COLUMNS},
          (select count(*) from knowledge_documents d where d.base_id = b.id)::int as documents_total
        from knowledge_bases b
        where b.id = %s
        """,
        (base_id,),
    ).fetchone()


def create_base(
    conn, workspace_id: UUID, tenant_organization_id: UUID, name: str, description: str | None, created_by: UUID
) -> UUID:
    return conn.execute(
        """
        insert into knowledge_bases (tenant_organization_id, workspace_id, name, description, created_by)
        values (%s, %s, %s, %s, %s)
        returning id
        """,
        (tenant_organization_id, workspace_id, name, description, created_by),
    ).fetchone()["id"]


def list_documents(conn, base_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        f"select {DOC_COLUMNS} from knowledge_documents d where d.base_id = %s order by d.created_at desc",
        (base_id,),
    ).fetchall()


def find_document(conn, document_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"select {DOC_COLUMNS}, b.workspace_id from knowledge_documents d "
        "join knowledge_bases b on b.id = d.base_id where d.id = %s",
        (document_id,),
    ).fetchone()


def create_document(conn, base_id: UUID, payload: dict[str, Any], created_by: UUID) -> UUID:
    return conn.execute(
        """
        insert into knowledge_documents (
          base_id, title, source_kind, storage_key, mime_type, size_bytes, created_by
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            base_id,
            payload["title"],
            payload.get("source_kind", "text"),
            payload.get("storage_key"),
            payload.get("mime_type"),
            payload.get("size_bytes"),
            created_by,
        ),
    ).fetchone()["id"]


def mark_failed(conn, document_id: UUID, reason: str) -> None:
    """Documento que falhou continua VISÍVEL, com o motivo.

    Sumir com ele faria a pessoa reenviar para sempre sem entender por quê — e
    o motivo (PDF escaneado, arquivo corrompido) é exatamente o que ela precisa
    para resolver.
    """
    conn.execute(
        """
        update knowledge_documents
        set status = 'failed', failure_reason = %s, updated_at = now()
        where id = %s
        """,
        (reason, document_id),
    )


def latest_checksum(conn, document_id: UUID) -> str | None:
    row = conn.execute(
        """
        select checksum from knowledge_document_versions
        where document_id = %s order by version desc limit 1
        """,
        (document_id,),
    ).fetchone()
    return row["checksum"] if row else None


def save_version_with_chunks(
    conn,
    document_id: UUID,
    texto: str,
    checksum: str,
    chunks: list[dict[str, Any]],
    created_by: UUID,
) -> int:
    """Grava a versão extraída e seus fragmentos, numa transação só.

    Versão e fragmentos são a mesma verdade: fragmento sem o texto de origem
    tem offset apontando para o nada. Gravar separado abriria a janela em que
    um existe sem o outro.
    """
    versao = conn.execute(
        "select coalesce(max(version), 0) + 1 as proxima from knowledge_document_versions where document_id = %s",
        (document_id,),
    ).fetchone()["proxima"]

    conn.execute(
        """
        insert into knowledge_document_versions (
          document_id, version, extracted_text, extracted_chars, checksum, created_by
        )
        values (%s, %s, %s, %s, %s, %s)
        """,
        (document_id, versao, texto, len(texto), checksum, created_by),
    )

    for chunk in chunks:
        conn.execute(
            """
            insert into knowledge_chunks (
              document_id, version, position, content, heading_path, heading_text,
              char_start, char_end
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                document_id,
                versao,
                chunk["position"],
                chunk["content"],
                chunk["heading_path"],
                # Mesma trilha, em texto, so para o indice. Coluna gerada exige
                # funcao IMMUTABLE e `array_to_string` e STABLE — sem esta
                # coluna o titulo ficaria fora da busca, que era o bug.
                " ".join(chunk["heading_path"]),
                chunk["char_start"],
                chunk["char_end"],
            ),
        )

    conn.execute(
        """
        update knowledge_documents
        set status = 'indexed', failure_reason = null, current_version = %s,
            chunks_total = %s, updated_at = now()
        where id = %s
        """,
        (versao, len(chunks), document_id),
    )
    return versao


def list_chunks(conn, document_id: UUID, version: int) -> list[dict[str, Any]]:
    return conn.execute(
        """
        select id, document_id, version, position, content, heading_path,
               char_start, char_end, is_active
        from knowledge_chunks
        where document_id = %s and version = %s
        order by position
        """,
        (document_id, version),
    ).fetchall()


def find_chunk(conn, chunk_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        """
        select c.id, c.document_id, c.version, c.position, c.content, c.heading_path,
               c.char_start, c.char_end, c.is_active, b.workspace_id
        from knowledge_chunks c
        join knowledge_documents d on d.id = c.document_id
        join knowledge_bases b on b.id = d.base_id
        where c.id = %s
        """,
        (chunk_id,),
    ).fetchone()


def set_chunk_active(conn, chunk_id: UUID, is_active: bool) -> bool:
    row = conn.execute(
        "update knowledge_chunks set is_active = %s where id = %s returning id",
        (is_active, chunk_id),
    ).fetchone()
    return row is not None


def get_version_text(conn, document_id: UUID, version: int) -> str | None:
    row = conn.execute(
        "select extracted_text from knowledge_document_versions where document_id = %s and version = %s",
        (document_id, version),
    ).fetchone()
    return row["extracted_text"] if row else None


def search(conn, workspace_id: UUID, base_id: UUID | None, termo: str, limit: int) -> list[dict[str, Any]]:
    """Busca LEXICAL (Fase 1). Sem embeddings, e a API diz isso ao chamador.

    Só a versão CORRENTE de cada documento e só fragmento ativo: versão antiga
    responder junto faria a base citar um texto que já foi substituído.
    """
    return conn.execute(
        """
        select c.id as chunk_id, c.content, c.heading_path, c.char_start, c.char_end,
               c.position, c.version,
               d.id as document_id, d.title as document_title,
               b.id as base_id, b.name as base_name,
               ts_rank(c.search_vector, websearch_to_tsquery('simple', %s)) as rank
        from knowledge_chunks c
        join knowledge_documents d on d.id = c.document_id and d.current_version = c.version
        join knowledge_bases b on b.id = d.base_id
        where b.workspace_id = %s
          and (%s::uuid is null or b.id = %s)
          and b.status = 'active'
          and c.is_active
          and c.search_vector @@ websearch_to_tsquery('simple', %s)
        order by rank desc, d.created_at desc, c.position asc
        limit %s
        """,
        (termo, workspace_id, base_id, base_id, termo, limit),
    ).fetchall()
