from pathlib import Path
import os
import sys

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import cleanup, migrate, seed_knowledge  # noqa: E402


def main() -> None:
    migrate.main()
    # Base de conhecimento (ideias, stack, docs) do seed_data para o banco.
    # Idempotente e nunca sobrescreve edição feita dentro do produto; é assim
    # que staging/produção recebem o que antes só existia no monorepo local.
    try:
        seed_knowledge.main()
    except Exception as error:  # noqa: BLE001
        print(f"seed_knowledge falhou (seguindo com o boot): {error}")
    # Retenção LGPD: limpar sessões/convites/resets vencidos a cada boot.
    # Nunca pode impedir a API de subir.
    try:
        cleanup.main()
    except Exception as error:  # noqa: BLE001
        print(f"cleanup falhou (seguindo com o boot): {error}")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("bioma_api.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
