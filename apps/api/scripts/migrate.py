from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect  # noqa: E402

MIGRATIONS = ROOT / "migrations"


def main() -> None:
    with connect() as conn:
        conn.execute(
            """
            create table if not exists schema_migrations (
              version text primary key,
              applied_at timestamptz not null default now()
            )
            """
        )
        applied = {
            row["version"]
            for row in conn.execute("select version from schema_migrations").fetchall()
        }

        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in applied:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("insert into schema_migrations (version) values (%s)", (path.name,))
            print(f"applied {path.name}")


if __name__ == "__main__":
    main()
