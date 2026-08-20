"""Cobertura REAL do Bioma: testes puros + smokes, num numero so.

Motivo de existir: `pytest --cov` sozinho reporta ~23%, e esse numero mente por
omissao. Os smokes exercitam a maior parte do sistema contra Postgres real, mas
rodam em SUBPROCESSOS — e subprocesso nao entra na medicao a menos que se ligue
`COVERAGE_PROCESS_START` mais o hook de startup do coverage.

Perseguir os 23% levaria ao pior desfecho possivel: escrever teste unitario
para codigo que JA tem smoke, so para levantar um numero que ignorava o smoke.

Uso:
    python scripts/coverage_report.py            # so os testes puros (rapido)
    python scripts/coverage_report.py --smokes   # inclui os smokes (lento, exige Postgres)
"""

from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
def limpar() -> None:
    """Apaga dados de execucoes anteriores.

    `parallel = true` faz cada processo escrever um arquivo com sufixo proprio;
    sem limpar, uma rodada nova soma com a antiga e a cobertura so sobe — o que
    e pior que nao medir, porque parece progresso.
    """
    for resto in ROOT.glob(".coverage*"):
        if resto.is_file():
            resto.unlink()


def ambiente_com_subprocesso() -> dict:
    """Faz os subprocessos Python medirem cobertura tambem.

    `COVERAGE_PROCESS_START` sozinho nao basta: o coverage so se liga no
    subprocesso se `coverage.process_startup()` rodar na inicializacao — o
    gancho oficial e um .pth no site-packages, criado por `limpar_hook()`.

    Os arquivos ficam no diretorio padrao (ROOT), com sufixo por processo, e
    `coverage combine` junta tudo depois.
    """
    env = dict(os.environ)
    env["COVERAGE_PROCESS_START"] = str(ROOT / ".coveragerc")
    return env


def instalar_hook_de_subprocesso() -> Path | None:
    """Cria o .pth que liga o coverage em todo subprocesso Python.

    Sem ele, os 59 smokes (um processo cada) nao entram na conta — que e
    exatamente o motivo de a medicao ingenua reportar 23%.
    """
    import sysconfig

    site_packages = Path(sysconfig.get_paths()["purelib"])
    pth = site_packages / "bioma_coverage_subprocess.pth"
    pth.write_text("import coverage; coverage.process_startup()" + chr(10), encoding="utf-8")
    return pth


def main() -> None:
    parser = argparse.ArgumentParser(description="Cobertura do Bioma")
    parser.add_argument("--smokes", action="store_true", help="Inclui os smokes (exige Postgres de pe)")
    args = parser.parse_args()

    limpar()
    env = ambiente_com_subprocesso()
    python = sys.executable
    pth = instalar_hook_de_subprocesso() if args.smokes else None

    print("== testes puros ==")
    subprocess.run(
        [python, "-m", "coverage", "run", "--rcfile", str(ROOT / ".coveragerc"), "-m", "pytest", "-q"],
        cwd=ROOT, env=env, check=False,
    )

    if args.smokes:
        print("\n== smokes (Postgres real) ==")
        subprocess.run(
            [python, str(REPO / "bioma" / "scripts" / "run_smokes.py")],
            cwd=REPO, env=env, check=False,
        )

    if pth and pth.exists():
        pth.unlink()  # o hook e temporario: deixar ligado mede tudo, sempre

    subprocess.run([python, "-m", "coverage", "combine"], cwd=ROOT, env=env, check=False)
    print("\n== cobertura ==")
    subprocess.run(
        [python, "-m", "coverage", "report", "--rcfile", str(ROOT / ".coveragerc")],
        cwd=ROOT, env=env, check=False,
    )
    print(
        "\nLembrete: cobertura mede LINHA EXECUTADA, nao comportamento verificado.\n"
        "Os bugs desta semana (claim_next_sync sem workspace_id, feature key\n"
        "inexistente abrindo gate, PDF afirmando ROI positivo) passariam por\n"
        "100% de cobertura sem serem vistos."
    )


if __name__ == "__main__":
    main()
