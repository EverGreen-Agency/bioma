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



def seed_cases(conn) -> int:
    """Acervo de cases da EG (migração 0103).

    Mesma regra de sobrescrita dos documentos: só atualiza o que ele mesmo
    semeou. Case editado dentro do Bioma nunca é revertido por redeploy — e
    isso vale especialmente para o estado de autorização, que é a razão de o
    acervo ter vindo para o banco.

    O conteúdo foi extraído dos arrays `casesPt/casesEn` do repo do site, que
    seguem existindo como fallback: uma apresentação comercial não pode ficar
    em branco porque a API estava reiniciando.
    """
    source = SEED_DIR / "cases.json"
    if not source.is_file():
        return 0
    cases = json.loads(source.read_text(encoding="utf-8"))
    tombstones = _get_tombstones(conn, "case")
    count = 0
    for case in cases:
        slug, deck = case["slug"], case["deck"]
        if f"{deck}::{slug}" in tombstones:
            continue
        row = conn.execute(
            """
            insert into eg_cases (
              deck, slug, display_order, client_named,
              consent_status, consent_note, status, seeded
            )
            values (%s, %s, %s, %s, %s, %s, %s, true)
            on conflict (deck, slug) do update set
              display_order = excluded.display_order,
              client_named = excluded.client_named,
              consent_status = excluded.consent_status,
              consent_note = excluded.consent_note,
              status = excluded.status,
              updated_at = now()
            where eg_cases.seeded = true
            returning id
            """,
            (
                deck, slug, case.get("order", 0), case["client_named"],
                case["consent_status"], case.get("note"), case["status"],
            ),
        ).fetchone()
        if row is None:
            # já existe e foi editado dentro do produto: não mexemos
            continue
        case_id = row["id"]
        for lang, body in case["langs"].items():
            conn.execute(
                """
                insert into eg_case_translations (
                  case_id, lang, name, category, headline,
                  metric, evidence, highlights, sections
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (case_id, lang) do update set
                  name = excluded.name,
                  category = excluded.category,
                  headline = excluded.headline,
                  metric = excluded.metric,
                  evidence = excluded.evidence,
                  highlights = excluded.highlights,
                  sections = excluded.sections,
                  updated_at = now()
                """,
                (
                    case_id, lang, body["name"], body["category"], body["headline"],
                    body["metric"], body["evidence"],
                    json.dumps(body["highlights"], ensure_ascii=False),
                    json.dumps(body["sections"], ensure_ascii=False),
                ),
            )
        count += 1
    return count


def seed_blog_posts(conn) -> int:
    """Fila editorial do blog (migração 0104).

    Os posts vêm de `seed_data/posts/*.md` com frontmatter simples. Mesma regra
    de sobrescrita: só atualiza o que ele mesmo semeou, então post editado
    dentro do Bioma nunca é revertido por redeploy.
    """
    directory = SEED_DIR / "posts"
    if not directory.is_dir():
        return 0
    tombstones = _get_tombstones(conn, "blog_post")
    count = 0
    for path in sorted(directory.glob("*.md")):
        if path.name in tombstones:
            continue
        raw = path.read_text(encoding="utf-8")
        meta: dict[str, str] = {}
        body = raw
        if raw.startswith("---"):
            head, _, body = raw[3:].partition(chr(10) + "---" + chr(10))
            for line in head.strip().splitlines():
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
        conn.execute(
            """
            insert into eg_blog_posts (
              slug, title, excerpt, content, target_keyword,
              search_volume, difficulty, intent, planned_month, status, seeded
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft', true)
            on conflict (slug) do update set
              title = excluded.title,
              excerpt = excluded.excerpt,
              content = excluded.content,
              target_keyword = excluded.target_keyword,
              search_volume = excluded.search_volume,
              difficulty = excluded.difficulty,
              intent = excluded.intent,
              planned_month = excluded.planned_month,
              updated_at = now()
            where eg_blog_posts.seeded = true
            """,
            (
                meta.get("slug", path.stem), meta.get("title", path.stem),
                meta.get("excerpt"), body.strip(), meta.get("keyword"),
                int(meta["volume"]) if meta.get("volume", "").isdigit() else None,
                int(meta["kd"]) if meta.get("kd", "").isdigit() else None,
                meta.get("intent"), meta.get("month"),
            ),
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
        cases = seed_cases(conn)
        posts = seed_blog_posts(conn)
    print(
        f"seed_knowledge: {ideas} ideia(s), {techs} tecnologia(s), "
        f"{docs} documento(s), {engineering} arquivo(s) de engenharia, "
        f"{ideas_docs} doc(s) de ideias, {cases} case(s), {posts} post(s)."
    )


if __name__ == "__main__":
    main()

