"""O script de cobertura não pode apagar a própria configuração.

A primeira versão limpava com `ROOT.glob(".coverage*")` — e esse glob casa com
`.coveragerc`. O script apagava o arquivo que ele mesmo precisa ler, e a rodada
seguinte morria com "Couldn't read '.coveragerc' as a config file".

O sintoma foi perfeito de enganoso: o erro apontava para o `.coveragerc` estar
corrompido, quando o arquivo simplesmente não existia mais.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _carregar_script():
    spec = importlib.util.spec_from_file_location(
        "coverage_report", ROOT / "scripts" / "coverage_report.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    modulo = _carregar_script()
    monkeypatch.setattr(modulo, "ROOT", tmp_path)
    return modulo, tmp_path


def test_limpar_nao_apaga_o_coveragerc(pasta):
    modulo, tmp_path = pasta
    config = tmp_path / ".coveragerc"
    config.write_text("[run]\n", encoding="utf-8")

    modulo.limpar()

    assert config.exists(), "o script apagou a propria configuracao"


def test_limpar_apaga_os_dados_de_execucoes_anteriores(pasta):
    """Sem limpar, `parallel = true` soma a rodada nova com a antiga e a
    cobertura so sobe — pior que nao medir, porque parece progresso."""
    modulo, tmp_path = pasta
    restos = [
        tmp_path / ".coverage",
        tmp_path / ".coverage.MAQUINA.1234.abcdef",
        tmp_path / ".coverage.outra.999.xyz",
    ]
    for resto in restos:
        resto.write_text("dado antigo", encoding="utf-8")

    modulo.limpar()

    assert not any(resto.exists() for resto in restos)


def test_limpar_nao_mexe_em_arquivo_alheio(pasta):
    modulo, tmp_path = pasta
    vizinho = tmp_path / ".coverage-notas.md"
    vizinho.write_text("anotacao", encoding="utf-8")

    modulo.limpar()

    assert vizinho.exists()


def test_o_caminho_do_runner_de_smokes_existe():
    """O script apontava para `bioma/bioma/scripts/run_smokes.py`.

    Caminho inexistente, `check=False` engolindo a falha: o script imprimia
    "== smokes ==" e seguia como se tivesse rodado. O numero final saia igual
    ao dos testes puros e parecia legitimo — a mesma classe do botao de sync
    que dizia sucesso sem sincronizar nada."""
    modulo = _carregar_script()
    assert modulo.RUN_SMOKES.exists(), f"runner nao existe em {modulo.RUN_SMOKES}"


def test_dados_de_cobertura_vao_todos_para_o_mesmo_lugar():
    """Os smokes rodam com outro cwd. Sem COVERAGE_FILE absoluto, os arquivos
    caem na pasta deles e o `combine` em ROOT nao acha nada — smoke medido,
    resultado descartado."""
    modulo = _carregar_script()
    env = modulo.ambiente_com_subprocesso()
    from pathlib import Path

    assert Path(env["COVERAGE_FILE"]).is_absolute()
    assert Path(env["COVERAGE_FILE"]).parent == modulo.ROOT
