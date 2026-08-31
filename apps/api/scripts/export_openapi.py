"""Exporta o OpenAPI da API para `packages/contracts/openapi.json` (CONTRACT-001).

Motivo: `apps/web/src/lib/api.ts` mantinha ~1.200 linhas de tipos escritos à
mão espelhando os schemas Pydantic. Nada garantia que os dois lados
concordassem — o drift só aparecia em runtime, e num repo editado por várias
sessões/LLMs em paralelo isso é a falha mais provável e mais silenciosa.

O arquivo gerado é versionado de propósito: o diff é a evidência de que o
contrato mudou. A CI roda este script e falha se o resultado divergir do que
está commitado (ver `.github/workflows/bioma-ci.yml`).

Uso:
    python scripts/export_openapi.py            # escreve o arquivo
    python scripts/export_openapi.py --check    # falha se estiver desatualizado
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT.parents[1] / "packages" / "contracts" / "openapi.json"


def build_spec() -> str:
    from bioma_api.main import app

    spec = app.openapi()
    # sort_keys estabiliza o diff: sem isso, a ordem do dict do FastAPI muda
    # entre execuções e a CI acusaria drift onde não houve mudança real.
    return json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta o contrato OpenAPI do Bioma")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Não escreve; sai com código 1 se o arquivo versionado estiver desatualizado",
    )
    args = parser.parse_args()

    spec = build_spec()

    if args.check:
        if not OUTPUT.exists():
            print(f"ERRO: {OUTPUT} não existe. Rode: python scripts/export_openapi.py")
            raise SystemExit(1)
        if OUTPUT.read_text(encoding="utf-8") != spec:
            print(
                "ERRO: o OpenAPI versionado está desatualizado.\n"
                "Rode `python scripts/export_openapi.py` e "
                "`npm run types:api` em apps/web, e commite o resultado."
            )
            raise SystemExit(1)
        print(f"contrato em dia: {OUTPUT}")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(spec, encoding="utf-8")
    print(f"contrato exportado: {OUTPUT} ({len(spec)} bytes)")


if __name__ == "__main__":
    main()
