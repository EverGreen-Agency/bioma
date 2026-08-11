"""Base de conhecimento da EG no banco (ideias, stack, documentos).

Substitui a leitura de `_opensquad/_memory/` do disco, que só funcionava na
máquina de quem desenvolve.
"""

from typing import Any
from uuid import UUID

IDEA_COLUMNS = (
    "id, slug, title, description, category, stage, horizon, origin, source, "
    "readiness, part_of, depends_on, enables, archived, created_at, updated_at"
)
TECH_COLUMNS = "id, slug, name, ring, quadrant, note, adr, source, created_at, updated_at"
DOC_COLUMNS = "id, path, category, title, content, seeded, updated_by, created_at, updated_at"


def list_ideas(conn) -> list[dict[str, Any]]:
    return conn.execute(f"select {IDEA_COLUMNS} from eg_ideas order by archived, stage, title").fetchall()


def upsert_ideas(conn, ideas: list[dict[str, Any]]) -> int:
    """Substitui o conjunto vindo da tela, preservando o que não veio.

    Não apaga o que ficou de fora do payload: a tela pode estar filtrando, e
    apagar em silêncio o que não está na tela seria perda de dado.
    """
    count = 0
    for item in ideas:
        slug = item.get("id") or item.get("slug")
        if not slug:
            continue
        conn.execute(
            """
            insert into eg_ideas (
              slug, title, description, category, stage, horizon, origin, source,
              readiness, part_of, depends_on, enables, archived, seeded
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false)
            on conflict (slug) do update set
              title = excluded.title, description = excluded.description,
              category = excluded.category, stage = excluded.stage,
              horizon = excluded.horizon, origin = excluded.origin,
              source = excluded.source, readiness = excluded.readiness,
              part_of = excluded.part_of, depends_on = excluded.depends_on,
              enables = excluded.enables, archived = excluded.archived,
              -- Escrita pela tela tira o registro do controle do seeder.
              seeded = false, updated_at = now()
            """,
            (
                slug,
                item.get("title") or slug,
                item.get("desc") or item.get("description"),
                item.get("category"),
                item.get("stage"),
                item.get("horizon"),
                item.get("origin"),
                item.get("source"),
                item.get("readiness"),
                item.get("part_of"),
                list(item.get("depends_on") or []),
                list(item.get("enables") or []),
                bool(item.get("archived")),
            ),
        )
        count += 1
    return count


def list_techs(conn) -> list[dict[str, Any]]:
    return conn.execute(f"select {TECH_COLUMNS} from eg_stack_techs order by ring, quadrant, name").fetchall()


def upsert_techs(conn, techs: list[dict[str, Any]]) -> int:
    count = 0
    for item in techs:
        slug = item.get("id") or item.get("slug")
        if not slug:
            continue
        conn.execute(
            """
            insert into eg_stack_techs (slug, name, ring, quadrant, note, adr, source, seeded)
            values (%s, %s, %s, %s, %s, %s, %s, false)
            on conflict (slug) do update set
              name = excluded.name, ring = excluded.ring, quadrant = excluded.quadrant,
              note = excluded.note, adr = excluded.adr, source = excluded.source,
              seeded = false, updated_at = now()
            """,
            (
                slug,
                item.get("name") or slug,
                item.get("ring") or "assess",
                item.get("quadrant") or "tools",
                item.get("note"),
                item.get("adr"),
                item.get("source"),
            ),
        )
        count += 1
    return count


def list_docs(conn, category: str | None = None) -> list[dict[str, Any]]:
    if category:
        return conn.execute(
            f"select {DOC_COLUMNS} from eg_knowledge_docs where category = %s order by title",
            (category,),
        ).fetchall()
    return conn.execute(f"select {DOC_COLUMNS} from eg_knowledge_docs order by category, title").fetchall()


def list_doc_titles(conn, limit: int = 200) -> list[dict[str, Any]]:
    """Índice do conhecimento da EG: categoria, título e caminho — sem conteúdo.

    O copiloto usa isto para saber que a resposta existe e onde encontrá-la. O
    texto completo de 30+ documentos não caberia no contexto, e mandar tudo a
    cada turno pagaria token por informação que a pergunta não usa.
    """
    return conn.execute(
        "select category, title, path from eg_knowledge_docs order by category, title limit %s",
        (limit,),
    ).fetchall()


def get_doc(conn, path: str) -> dict[str, Any] | None:
    return conn.execute(f"select {DOC_COLUMNS} from eg_knowledge_docs where path = %s", (path,)).fetchone()


def save_doc(conn, path: str, content: str, updated_by: UUID) -> dict[str, Any] | None:
    """Marca `seeded = false`: a partir daqui o redeploy não sobrescreve mais."""
    return conn.execute(
        f"""
        update eg_knowledge_docs
        set content = %s, seeded = false, updated_by = %s, updated_at = now()
        where path = %s
        returning {DOC_COLUMNS}
        """,
        (content, updated_by, path),
    ).fetchone()


def create_doc(
    conn, path: str, category: str, title: str, content: str, updated_by: UUID
) -> dict[str, Any]:
    """Documento criado dentro do produto nasce com `seeded = false`: nunca foi
    semente, então o deploy não tem o que reverter."""
    return conn.execute(
        f"""
        insert into eg_knowledge_docs (path, category, title, content, seeded, updated_by)
        values (%s, %s, %s, %s, false, %s)
        on conflict (path) do update set
          content = excluded.content, title = excluded.title,
          seeded = false, updated_by = excluded.updated_by, updated_at = now()
        returning {DOC_COLUMNS}
        """,
        (path, category, title, content, updated_by),
    ).fetchone()


def search_docs(conn, term: str, limit: int = 10) -> list[dict[str, Any]]:
    """Busca simples para o copiloto usar o conhecimento como dossiê."""
    return conn.execute(
        """
        select id, path, category, title, left(content, 1200) as excerpt
        from eg_knowledge_docs
        where title ilike '%%' || %s || '%%' or content ilike '%%' || %s || '%%'
        order by title
        limit %s
        """,
        (term, term, limit),
    ).fetchall()


def delete_idea(conn, slug: str) -> None:
    conn.execute("insert into eg_tombstones (entity_type, slug) values ('idea', %s) on conflict do nothing", (slug,))
    conn.execute("delete from eg_ideas where slug = %s", (slug,))


def delete_doc(conn, path: str) -> None:
    conn.execute("insert into eg_tombstones (entity_type, slug) values ('doc', %s) on conflict do nothing", (slug,))
    conn.execute("delete from eg_knowledge_docs where path = %s", (path,))

