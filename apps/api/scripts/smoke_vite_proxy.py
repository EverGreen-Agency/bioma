"""Garante que o proxy do dev server cobre todos os prefixos da API.

Por que existe: o `vite.config.mjs` listava 5 prefixos enquanto a API tinha 30.
Toda chamada para um prefixo ausente caía no fallback SPA do Vite, que devolve
`index.html` — e a tela quebrava com
`Unexpected token '<', "<!doctype "... is not valid JSON`.

Isso só acontece em desenvolvimento (em produção o front fala com a API direto),
então passava despercebido até alguém abrir a tela. Este smoke transforma
"esqueci de adicionar o prefixo" em falha de CI.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.main import app  # noqa: E402

VITE_CONFIG = ROOT.parent / "web" / "vite.config.mjs"

# Prefixos que o front nunca chama pelo dev server (ou que não são rotas de API).
IGNORED = {"docs", "redoc", "openapi.json"}


def api_prefixes() -> set[str]:
    prefixes = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/"):
            continue
        parts = path.split("/")
        if len(parts) < 2 or not parts[1] or parts[1].startswith("{"):
            continue
        prefixes.add(parts[1])
    return prefixes


def proxied_prefixes() -> set[str]:
    if not VITE_CONFIG.exists():
        raise AssertionError(f"vite.config.mjs não encontrado em {VITE_CONFIG}")
    content = VITE_CONFIG.read_text(encoding="utf-8")
    return {match.strip("/") for match in re.findall(r'"(/[a-z0-9._-]+)"', content)}


def main() -> None:
    api = api_prefixes()
    proxied = proxied_prefixes()
    missing = sorted(prefix for prefix in api - proxied if prefix not in IGNORED)

    if missing:
        raise AssertionError(
            "Prefixos da API ausentes no proxy do Vite (a tela vai receber HTML "
            f"em vez de JSON em dev): {', '.join(missing)}.\n"
            "Adicione em bioma/apps/web/vite.config.mjs -> API_PREFIXES."
        )

    print(f"proxy do Vite cobre os {len(api)} prefixos da API — OK")


if __name__ == "__main__":
    main()
