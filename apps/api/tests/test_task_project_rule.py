"""Decisão 13: tarefa de CLIENTE exige projeto; tarefa da EG não.

Estes testes existem porque a regra foi escrita, documentada e ficou MORTA: as
três queries de contexto (`find_workspace_context`, `find_list_context`,
`find_task_context`) não selecionavam `w.kind`, então `context.get(...)` devolvia
`None` para todo mundo e o guard nunca disparava. Cobertura de linha não pegaria
— a linha executava e liberava.

O antídoto aqui é duplo: testar o COMPORTAMENTO da regra e testar que todo
caminho de escrita a aplica. O segundo é o que faltava.
"""

import inspect

import pytest
from fastapi import HTTPException

from bioma_api.repositories import tasks as tasks_repo
from bioma_api.services import tasks as tasks_service


AGENCIA = {"workspace_id": "w-eg", "workspace_kind": "agency_internal"}
CLIENTE = {"workspace_id": "w-cli", "workspace_kind": "client"}


@pytest.fixture
def projeto_sempre_do_workspace(monkeypatch):
    monkeypatch.setattr(tasks_repo, "project_belongs_to_workspace", lambda *_: True)


def test_cliente_sem_projeto_e_recusado():
    with pytest.raises(HTTPException) as erro:
        tasks_service._validate_project(None, "w-cli", {"project_id": None}, CLIENTE)
    assert erro.value.status_code == 422
    # A mensagem tem que dizer ONDE resolver, não só que está errado.
    assert "Projetos e contratos" in erro.value.detail


def test_operacao_eg_sem_projeto_e_permitida():
    """Demanda interna legítima existe sem projeto (treinamento, social da casa).
    Exigir projeto aqui obrigaria a inventar um projeto 'diversos'."""
    tasks_service._validate_project(None, "w-eg", {"project_id": None}, AGENCIA)


def test_cliente_com_projeto_passa(projeto_sempre_do_workspace):
    tasks_service._validate_project(None, "w-cli", {"project_id": "p-1"}, CLIENTE)


def test_projeto_de_outro_workspace_e_recusado(monkeypatch):
    monkeypatch.setattr(tasks_repo, "project_belongs_to_workspace", lambda *_: False)
    with pytest.raises(HTTPException) as erro:
        tasks_service._validate_project(None, "w-cli", {"project_id": "p-de-outro"}, CLIENTE)
    assert erro.value.status_code == 422
    assert "mesmo workspace" in erro.value.detail


def test_contexto_ausente_falha_alto_em_vez_de_liberar():
    """O bug original em uma linha.

    Quando o contexto não traz o tipo do workspace, a regra NÃO pode simplesmente
    liberar — foi assim que ela morreu em silêncio. Tem que explodir."""
    with pytest.raises(KeyError):
        tasks_service._validate_project(None, "w-cli", {"project_id": None}, {})


def test_regra_nao_tem_como_ser_esquecida():
    """`context` não pode ter valor padrão.

    Era opcional, e dois dos três caminhos de escrita simplesmente não passavam.
    Sem default, esquecer vira TypeError na hora, não permissão indevida em
    produção."""
    parametros = inspect.signature(tasks_service._validate_project).parameters
    assert parametros["context"].default is inspect.Parameter.empty


@pytest.mark.parametrize(
    "consulta",
    ["find_workspace_context", "find_list_context", "find_task_context"],
)
def test_toda_query_de_contexto_carrega_o_tipo_do_workspace(consulta):
    """Asserção sobre o TEXTO do SQL — de propósito.

    O teste puro não tem banco, então não dá para conferir a linha devolvida.
    Mas dá para conferir que a coluna foi pedida, e era exatamente isso que
    faltava nas três. Um smoke cobre o resto contra Postgres de verdade."""
    sql = inspect.getsource(getattr(tasks_repo, consulta))
    assert "workspace_kind" in sql, f"{consulta} não devolve o tipo do workspace"


class TestAtualizacaoParcial:
    """PATCH sem `project_id` quer dizer "nao mexe no projeto".

    A primeira versao da regra tratava ausente e nulo como a mesma coisa, e o
    resultado foi que editar QUALQUER campo de uma tarefa de cliente passou a
    ser recusado — mudar o titulo exigia reenviar o projeto. Quem pegou foi o
    smoke_tasks, nao o teste puro: o caminho de update so aparece com banco.
    """

    def test_campo_ausente_nao_dispara_a_exigencia(self):
        tasks_service._validate_project(
            None, "w-cli", {"title": "novo titulo"}, CLIENTE, partial=True
        )

    def test_projeto_explicitamente_nulo_ainda_e_recusado(self):
        """Mandar `project_id: null` de proposito E tentar desvincular, e isso
        continua proibido em cliente."""
        with pytest.raises(HTTPException) as erro:
            tasks_service._validate_project(
                None, "w-cli", {"project_id": None}, CLIENTE, partial=True
            )
        assert erro.value.status_code == 422

    def test_na_criacao_ausente_continua_sendo_recusado(self):
        """Criar sem projeto e criar orfao — o caso que a decisao 13 existe
        para impedir. `partial` nao pode afrouxar isso."""
        with pytest.raises(HTTPException):
            tasks_service._validate_project(None, "w-cli", {"title": "x"}, CLIENTE)
