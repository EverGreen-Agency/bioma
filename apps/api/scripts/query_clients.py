"""Lista rápida de clientes (debug local). Usa a conexão do projeto."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect  # noqa: E402


def main() -> None:
    with connect() as conn:
        for row in conn.execute("select id, name, status from clients order by created_at").fetchall():
            print(f"{row['id']}  {row['name']}  ({row['status']})")


if __name__ == "__main__":
    main()
