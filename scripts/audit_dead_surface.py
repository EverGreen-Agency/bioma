"""Auditoria de superfície morta do Bioma.

O padrão de falha dominante deste codebase não é lógica errada — é código
construído e nunca ligado. Este script detecta mecanicamente três classes:

1. EXPORTS ÓRFÃOS (web): componente/função exportada que nenhum outro arquivo
   importa. Foi o caso do BriefingPanel, que existiu meses sem rota.
2. COLUNAS NUNCA LIDAS (banco): coluna criada em migração cujo nome não aparece
   em nenhum código de backend. Foi o caso de `recurrence` sem regra de negócio.
3. RÓTULOS DE AGREGAÇÃO (heurística): textos de UI que prometem totais
   ("todos", "ativos", "total") — lista para revisão humana; foi o caso do
   "4 clientes ativos" que contava onboarding.

Uso:  python bioma/scripts/audit_dead_surface.py [--max-labels N]
Sem custo de API; roda só com stdlib. Saída em texto; código de saída 0 sempre
(é relatório, não gate).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WEB_SRC = REPO / "apps" / "web" / "src"
MIGRATIONS = REPO / "apps" / "api" / "migrations"
BACKEND_DIRS = [REPO / "apps" / "api" / "bioma_api", REPO / "apps" / "worker" / "bioma_worker"]

# Entradas que não precisam de importador (bootstrapping/roteamento raiz).
ENTRYPOINT_FILES = {"main.tsx", "App.tsx", "vite-env.d.ts"}

# Colunas de infraestrutura presentes em quase toda tabela; a ausência do nome
# no backend não significa nada para elas.
BASELINE_COLUMNS = {"id", "created_at", "updated_at"}

EXPORT_RE = re.compile(
    r"^export\s+(?:default\s+)?(?:async\s+)?(?:function|const|class)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
CREATE_TABLE_RE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-z_]+)\s*\((.*?)\);", re.S | re.I)
ADD_COLUMN_RE = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?([a-z_]+)\s+add\s+column\s+(?:if\s+not\s+exists\s+)?([a-z_]+)", re.I
)
# Sem estes dois, migrações posteriores que removem colunas/tabelas ficam
# invisíveis e o relatório acusa como "morto" o que já não existe no banco.
DROP_COLUMN_RE = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?([a-z_]+)\s+drop\s+column\s+(?:if\s+exists\s+)?([a-z_]+)", re.I
)
DROP_TABLE_RE = re.compile(r"drop\s+table\s+(?:if\s+exists\s+)?([a-z_]+)", re.I)
COLUMN_LINE_RE = re.compile(r"^\s*([a-z_]+)\s+(?:uuid|text|int|bigint|numeric|boolean|timestamptz|date|jsonb|serial|float|double|varchar|char)", re.I)
LABEL_RE = re.compile(r"[>\"'`]([^<>\"'`{}]*\b(?:todos|todas|total|ativos|ativas)\b[^<>\"'`{}]*)[<\"'`]", re.I)


def web_files() -> list[Path]:
    return [p for p in WEB_SRC.rglob("*") if p.suffix in (".ts", ".tsx") and "__pycache__" not in p.parts]


def find_orphan_exports() -> list[tuple[str, str]]:
    files = web_files()
    contents = {path: path.read_text(encoding="utf-8", errors="replace") for path in files}

    exports: dict[str, list[Path]] = defaultdict(list)
    for path, text in contents.items():
        if path.name in ENTRYPOINT_FILES or path.name.endswith(".d.ts"):
            continue
        for match in EXPORT_RE.finditer(text):
            exports[match.group(1)].append(path)

    orphans: list[tuple[str, str]] = []
    for name, declared_in in sorted(exports.items()):
        # Referência = o nome aparece em QUALQUER outro arquivo (import estático,
        # lazy `module.X`, re-export). Se não aparece em lugar nenhum, é órfão.
        used = any(
            re.search(rf"\b{re.escape(name)}\b", text)
            for path, text in contents.items()
            if path not in declared_in
        )
        if not used:
            rel = declared_in[0].relative_to(REPO)
            orphans.append((name, str(rel)))
    return orphans


def find_unread_columns() -> list[tuple[str, str]]:
    table_columns: set[tuple[str, str]] = set()
    for sql_file in sorted(MIGRATIONS.glob("*.sql")):
        sql = sql_file.read_text(encoding="utf-8", errors="replace")
        for table, body in CREATE_TABLE_RE.findall(sql):
            for line in body.splitlines():
                col = COLUMN_LINE_RE.match(line)
                if col and col.group(1) not in ("primary", "unique", "check", "constraint", "foreign"):
                    table_columns.add((table.lower(), col.group(1).lower()))
        for table, column in ADD_COLUMN_RE.findall(sql):
            table_columns.add((table.lower(), column.lower()))
        # Aplicadas na ordem das migrações: o que foi dropado sai do conjunto.
        for table, column in DROP_COLUMN_RE.findall(sql):
            table_columns.discard((table.lower(), column.lower()))
        for table in DROP_TABLE_RE.findall(sql):
            dropped = table.lower()
            table_columns = {pair for pair in table_columns if pair[0] != dropped}

    backend_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for base in BACKEND_DIRS
        for path in base.rglob("*.py")
        if "__pycache__" not in path.parts
    )

    unread: list[tuple[str, str]] = []
    for table, column in sorted(table_columns):
        if column in BASELINE_COLUMNS:
            continue
        # Se nem o nome da tabela aparece, a tabela inteira é morta — reporta uma vez.
        if not re.search(rf"\b{re.escape(column)}\b", backend_text):
            unread.append((table, column))
    return unread


def find_aggregation_labels(max_labels: int) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in web_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), start=1):
            for match in LABEL_RE.finditer(line):
                label = match.group(1).strip()
                if len(label) < 5 or len(label) > 80:
                    continue
                hits.append((str(path.relative_to(REPO)), i, label))
    return hits[:max_labels]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-labels", type=int, default=25)
    args = parser.parse_args()

    print("=" * 72)
    print("AUDITORIA DE SUPERFÍCIE MORTA — Bioma")
    print("=" * 72)

    orphans = find_orphan_exports()
    print(f"\n[1] EXPORTS SEM IMPORTADOR ({len(orphans)}) — construído mas não ligado:")
    for name, rel in orphans:
        print(f"  - {name}  ({rel})")
    if not orphans:
        print("  nenhum — tudo que é exportado é importado em algum lugar.")

    unread = find_unread_columns()
    print(f"\n[2] COLUNAS DE MIGRAÇÃO NUNCA CITADAS NO BACKEND ({len(unread)}):")
    by_table: dict[str, list[str]] = defaultdict(list)
    for table, column in unread:
        by_table[table].append(column)
    for table, columns in sorted(by_table.items()):
        print(f"  - {table}: {', '.join(columns)}")
    if not unread:
        print("  nenhuma.")

    labels = find_aggregation_labels(args.max_labels)
    print(f"\n[3] RÓTULOS DE AGREGAÇÃO PARA REVISÃO HUMANA (heurística, primeiros {args.max_labels}):")
    print("    (conferir se a query por trás realmente agrega o que o texto promete)")
    for rel, line, label in labels:
        print(f"  - {rel}:{line}  «{label}»")
    if not labels:
        print("  nenhum.")

    print("\nRelatório concluído. Itens são candidatos a lixo/bug de fiação, não vereditos.")
    sys.exit(0)


if __name__ == "__main__":
    main()
