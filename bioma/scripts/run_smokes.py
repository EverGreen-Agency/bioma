"""Runner de smokes do Bioma — descobre e executa todos, um por processo.

Motivo de existir: a CI listava 4 smokes na mão enquanto o repositório tinha 40+.
Todo smoke novo nascia fora da CI, e foi assim que um 500 em toda a ingestão de
transcrição do copiloto de vendas passou meses sem ser visto.

Regra: **descoberta automática**. Um smoke novo entra na CI só por existir. Se um
smoke não pode rodar na CI, ele entra em `SKIP` aqui com o motivo escrito — o que
transforma "não roda" em decisão registrada, em vez de esquecimento.

Uso:
    python bioma/scripts/run_smokes.py                 # todos os elegíveis
    python bioma/scripts/run_smokes.py --group mutable # só os que exigem banco isolado
    python bioma/scripts/run_smokes.py --list          # lista sem executar
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SMOKE_DIRS = [REPO / "apps" / "api" / "scripts", REPO / "apps" / "worker" / "scripts"]

# Smokes que exigem o banco isolado (guarda de sufixo _smoke) — a CI os roda em
# um passo separado, depois de provisionar `bioma_smoke`.
MUTABLE = {
    "smoke_queue",
    "smoke_vault",
    "smoke_reaper",
    # Estes recusam rodar fora de banco _smoke/_test (guarda no próprio script):
    "smoke_ai_operations",
    "smoke_ai_control_plane",
    "smoke_cms_publish",
    "smoke_knowledge",
}

# Exclusões conscientes. Cada linha é uma decisão, não um esquecimento.
SKIP: dict[str, str] = {
    "smoke_support": "não é smoke: módulo de helpers importado pelos outros",
    "smoke_github_write": "escreve em repositório real do GitHub; precisa de token com escopo de escrita",
    "smoke_github_read": "depende de GITHUB_API_TOKEN válido",
    "smoke_remote": "aponta para ambiente remoto, não para o banco da CI",
    "smoke_kommo": "exige credencial real do Kommo",
    "smoke_oauth": "exige credenciais de OAuth do Google configuradas",
    "smoke_files": "exige storage de arquivos (S3/compatível) configurado; sem ele a API responde 503 por desenho",
}


# Smokes que vivem em apps/worker mas exercitam a API por TestClient: precisam do
# venv da API (o venv do worker não tem fastapi).
NEEDS_API_ENV = {"smoke_ai_content", "smoke_ai_control_plane"}

# smoke_api valida contagens agregadas da carteira, então precisa rodar antes dos
# smokes que criam dados no mesmo banco. Enquanto os smokes não forem isolados por
# transação (dívida registrada no handoff), a ordem resolve na prática.
ORDER_FIRST = ["smoke_api"]


def interpreter_for(path: Path) -> str:
    """Cada app tem venv próprio (o worker depende de google-auth, a API não).
    Rodar tudo com um único interpretador dava ModuleNotFoundError enganoso."""
    app_root = path.parent.parent
    if path.stem in NEEDS_API_ENV:
        app_root = REPO / "apps" / "api"
    for candidate in (
        app_root / ".venv" / "Scripts" / "python.exe",
        app_root / ".venv" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def discover(group: str) -> list[Path]:
    found: list[Path] = []
    for directory in SMOKE_DIRS:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("smoke_*.py")):
            name = path.stem
            if name in SKIP:
                continue
            is_mutable = name in MUTABLE
            if group == "mutable" and not is_mutable:
                continue
            if group == "standard" and is_mutable:
                continue
            found.append(path)
    rank = {name: index for index, name in enumerate(ORDER_FIRST)}
    return sorted(found, key=lambda item: (rank.get(item.stem, len(rank)), item.stem))


def purge_residue() -> None:
    """Varre o resíduo dos smokes que falharam no meio.

    A limpeza de cada smoke roda no `finally`; uma asserção quebrada ANTES do
    `try` escapa dela e o workspace fica na carteira. Roda no venv da API porque
    é lá que `smoke_support` importa `bioma_api.db`.
    """
    support = REPO / "apps" / "api" / "scripts" / "smoke_support.py"
    result = subprocess.run(
        [interpreter_for(support), str(support)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(support.parent.parent),
    )
    if result.returncode != 0:
        print(f"  aviso: varredura de resíduo falhou — {(result.stderr or '').strip()[-300:]}")
        return
    print(f"  faxina  resíduo de smoke: {(result.stdout or '').strip()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=["all", "standard", "mutable"], default="standard")
    parser.add_argument("--list", action="store_true", help="apenas listar")
    args = parser.parse_args()

    smokes = discover(args.group)

    if args.list:
        for path in smokes:
            print(path.relative_to(REPO))
        print(f"\n{len(smokes)} smoke(s) elegíveis no grupo '{args.group}'.")
        for name, reason in sorted(SKIP.items()):
            print(f"  ignorado: {name} — {reason}")
        return

    print(f"Executando {len(smokes)} smoke(s) do grupo '{args.group}'.\n")
    failures: list[tuple[str, str]] = []
    for path in smokes:
        label = path.stem
        started = time.monotonic()
        # Um processo por smoke: estado global de um não contamina o próximo, e o
        # traceback fica atribuído ao arquivo certo.
        result = subprocess.run(
            [interpreter_for(path), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(path.parent.parent),
        )
        elapsed = time.monotonic() - started
        if result.returncode == 0:
            print(f"  ok      {label}  ({elapsed:.1f}s)")
        else:
            print(f"  FALHOU  {label}  ({elapsed:.1f}s)")
            tail = (result.stdout or "") + (result.stderr or "")
            failures.append((label, tail.strip()[-1500:]))

    purge_residue()

    print()
    if failures:
        for label, output in failures:
            print(f"===== {label} =====")
            # O console do Windows é cp1252 e explode em caractere fora dessa
            # tabela (acento vindo de subprocesso vira U+FFFD). Isso derrubava o
            # runner AQUI, no meio de imprimir o erro — e o traceback do
            # UnicodeEncodeError aparecia NO LUGAR da falha real, escondendo a
            # causa justamente quando ela importava.
            sys.stdout.buffer.write(
                output.encode(sys.stdout.encoding or "utf-8", errors="replace")
            )
            sys.stdout.buffer.write(b"\n\n")
            sys.stdout.flush()
        print(f"{len(failures)} de {len(smokes)} smoke(s) falharam.")
        sys.exit(1)

    print(f"Todos os {len(smokes)} smoke(s) passaram.")


if __name__ == "__main__":
    main()
