"""Provisiona o workspace interno da EG ("Operação EG").

Antes este script também criava um registro em `clients` chamado "EverGreen
Internal" — a agência como cliente de si mesma. Aquilo nunca foi um conceito,
era uma concessão: `performance_connections` exigia `client_id not null` e
`find_accessible_client` só resolvia workspace via junção com `clients`. Sem o
registro-fantasma, a Operação EG não conseguia conectar mídia nem resolver o
próprio contexto.

Com a migração 0087 (conexão pertence ao workspace) e o resolvedor ancorado em
`workspaces`, a concessão deixou de ser necessária — e o script deixou de
criá-la. A EG tem workspace; não tem contrato consigo mesma.

Se o registro antigo ainda existir no seu banco, ele é inofensivo, mas some da
carteira de qualquer jeito (`externalClients` filtra o slug `eg`). Para
removê-lo:

    delete from clients c using organizations o
     where o.id = c.organization_id and o.slug = 'eg';

Idempotente. Usa a conexão do projeto (DATABASE_URL), não string hardcoded.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect  # noqa: E402
from bioma_api.repositories import workspaces as workspaces_repo  # noqa: E402


def main() -> None:
    with connect() as conn:
        org = conn.execute("select id from organizations where slug = 'eg'").fetchone()
        if not org:
            raise SystemExit("Organização EG não encontrada — rode as migrations/seed antes.")

        workspaces_repo.provision_agency_workspace(conn, org["id"], "Operação EG")

        legacy = conn.execute(
            "select id, name from clients where organization_id = %s",
            (org["id"],),
        ).fetchone()
        if legacy:
            print(
                f"Aviso: registro de cliente legado ainda existe ({legacy['name']}). "
                "Ele não é mais usado; veja o docstring para removê-lo."
            )

    print("Workspace interno da EG provisionado.")


if __name__ == "__main__":
    main()
