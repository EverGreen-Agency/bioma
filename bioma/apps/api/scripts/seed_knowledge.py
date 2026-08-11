"""Importa a base de conhecimento de `seed_data/` para o Postgres.

Roda a cada boot (chamado por `start.py`, depois das migrações) e é
**idempotente**: reimportar não duplica nem sobrescreve edição feita dentro do
produto.

Por que este arquivo existe: Banco de Ideias, Stack e Arquitetura liam
`_opensquad/_memory/` do disco. Esse diretório fica FORA do contexto de build do
Dockerfile da API, então nunca existiu em staging/produção — as telas apareciam
vazias lá. Com o dado semeado no banco, elas passam a funcionar em qualquer
ambiente, e o repositório pode ser limpo.

Regra de sobrescrita: o seeder só atualiza o que ele mesmo semeou
(`seeded = true`). Vale para ideias, stack E documentos — qualquer registro
editado dentro do Bioma deixa de ser semente e nunca é revertido por redeploy.
"""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect  # noqa: E402

SEED_DIR = ROOT / "seed_data"


def _array(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value:
        return [str(value)]
    return []


def _get_tombstones(conn, entity_type: str) -> set[str]:
    try:
        rows = conn.execute(
            "select slug from eg_tombstones where entity_type = %s", (entity_type,)
        ).fetchall()
        return {r["slug"] for r in rows}
    except Exception:
        return set()


def seed_ideas(conn) -> int:
    path = SEED_DIR / "ideas.json"
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    tombstones = _get_tombstones(conn, "idea")
    count = 0
    for item in payload.get("ideas", []):
        slug = item.get("id")
        if not slug or slug in tombstones:
            continue
        conn.execute(
            """
            insert into eg_ideas (
              slug, title, description, category, stage, horizon, origin, source,
              readiness, part_of, depends_on, enables, archived, seeded
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
            on conflict (slug) do nothing
            """,
            (
                slug,
                item.get("title") or slug,
                item.get("desc"),
                item.get("category"),
                item.get("stage"),
                item.get("horizon"),
                item.get("origin"),
                item.get("source"),
                item.get("readiness"),
                item.get("part_of"),
                _array(item.get("depends_on")),
                _array(item.get("enables")),
                bool(item.get("archived")),
            ),
        )
        count += 1
    return count


def seed_stack(conn) -> int:
    path = SEED_DIR / "stack.json"
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    tombstones = _get_tombstones(conn, "tech")
    count = 0
    for item in payload.get("techs", []):
        slug = item.get("id")
        if not slug or slug in tombstones:
            continue
        conn.execute(
            """
            insert into eg_stack_techs (slug, name, ring, quadrant, note, adr, source, seeded)
            values (%s, %s, %s, %s, %s, %s, %s, true)
            on conflict (slug) do nothing
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


def seed_docs(conn) -> int:
    directory = SEED_DIR / "knowledge"
    if not directory.is_dir():
        return 0
    tombstones = _get_tombstones(conn, "doc")
    count = 0
    for path in sorted(directory.glob("*.md")):
        if path.name in tombstones:
            continue
        category, _, filename = path.name.partition("__")
        if category not in ("knowledge", "engineering", "architecture", "company"):
            category, filename = "knowledge", path.name
        content = path.read_text(encoding="utf-8", errors="replace")
        title = filename.removesuffix(".md")
        conn.execute(
            """
            insert into eg_knowledge_docs (path, category, title, content, seeded)
            values (%s, %s, %s, %s, true)
            on conflict (path) do update set
              content = excluded.content,
              title = excluded.title,
              updated_at = now()
            where eg_knowledge_docs.seeded = true
            """,
            (path.name, category, title, content),
        )
        count += 1
    return count


def seed_engineering(conn) -> int:
    """Specs, ADRs e tasks por módulo.

    O nome do arquivo achatado (`mod-x__spec.md`, `mod-x__adr__0001.md`) é a
    chave: preserva a hierarquia original sem precisar de tabela extra.
    """
    directory = SEED_DIR / "engineering"
    if not directory.is_dir():
        return 0
    tombstones = _get_tombstones(conn, "doc")
    count = 0
    for path in sorted(directory.glob("*.md")):
        doc_path = f"engineering/{path.name}"
        if doc_path in tombstones or path.name in tombstones:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        title = path.name.removesuffix(".md").replace("__", " / ")
        conn.execute(
            """
            insert into eg_knowledge_docs (path, category, title, content, seeded)
            values (%s, 'engineering', %s, %s, true)
            on conflict (path) do update set
              content = excluded.content, title = excluded.title, updated_at = now()
            where eg_knowledge_docs.seeded = true
            """,
            (doc_path, title, content),
        )
        count += 1
    return count


def seed_ideas_docs(conn) -> int:
    """Documentos detalhados do Banco de Ideias ("Ler Detalhes")."""
    directory = SEED_DIR / "ideas_docs"
    if not directory.is_dir():
        return 0
    tombstones = _get_tombstones(conn, "doc")
    count = 0
    for path in sorted(directory.glob("*.md")):
        doc_slug = path.name.removesuffix(".md")
        doc_path = f"ideas_docs/{path.name}"
        if doc_path in tombstones or doc_slug in tombstones:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        title = f"Ideia / {doc_slug}"
        for p in (doc_path, f"ideas/{doc_slug}.md"):
            conn.execute(
                """
                insert into eg_knowledge_docs (path, category, title, content, seeded)
                values (%s, 'ideas_docs', %s, %s, true)
                on conflict (path) do update set
                  content = excluded.content, title = excluded.title, updated_at = now()
                where eg_knowledge_docs.seeded = true
                """,
                (p, title, content),
            )
        count += 1
    return count



def main() -> None:
    if not SEED_DIR.is_dir():
        print("seed_knowledge: seed_data/ ausente, nada a importar.")
        return
    with connect() as conn:
        ideas = seed_ideas(conn)
        techs = seed_stack(conn)
        docs = seed_docs(conn)
        engineering = seed_engineering(conn)
        ideas_docs = seed_ideas_docs(conn)
    print(
        f"seed_knowledge: {ideas} ideia(s), {techs} tecnologia(s), "
        f"{docs} documento(s), {engineering} arquivo(s) de engenharia, "
        f"{ideas_docs} doc(s) de ideias."
    )


if __name__ == "__main__":
    main()

