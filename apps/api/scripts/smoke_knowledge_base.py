"""Smoke da base de conhecimento no Postgres, contra o banco real.

O que este smoke protege: Banco de Ideias, Stack e documentos liam
`_opensquad/_memory/` do disco — diretório que fica FORA do contexto de build do
Dockerfile e portanto nunca existiu em staging/produção. As telas apareciam
vazias lá e ninguém percebia.

Valida:
- as telas leem do banco (independem do monorepo estar presente);
- escrita persiste e não apaga o que ficou fora do payload;
- o seeder é idempotente e NÃO reverte edição feita dentro do produto;
- só EG.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.repositories import knowledge as repo

import seed_knowledge

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    client = TestClient(app)
    assert_status(client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login")

    # 1) Leitura vem do banco, não do disco.
    ideas = client.get("/backoffice/ideas")
    assert_status(ideas, 200, "listar ideias")
    stack = client.get("/backoffice/stack")
    assert_status(stack, 200, "listar stack")
    idea_count = len(ideas.json()["ideas"])
    tech_count = len(stack.json()["techs"])
    assert idea_count > 0 and tech_count > 0, f"base vazia: {idea_count} ideias, {tech_count} techs"
    print(f"leitura do Postgres OK — {idea_count} ideias, {tech_count} tecnologias")

    created_slug = "smoke-knowledge-idea"
    created_tech = "smoke-knowledge-tech"
    try:
        # 2) Escrita persiste e não apaga o resto.
        saved = client.post(
            "/backoffice/ideas",
            json={"ideas": [{"id": created_slug, "title": "Ideia do smoke", "desc": "x", "stage": "backlog"}]},
        )
        assert_status(saved, 200, "salvar ideia")
        after = client.get("/backoffice/ideas").json()["ideas"]
        assert any(row["id"] == created_slug for row in after), "ideia criada nao aparece"
        assert len(after) == idea_count + 1, (
            f"salvar 1 ideia mudou o total de {idea_count} para {len(after)} — payload parcial nao pode apagar o resto"
        )
        print("escrita persiste sem apagar o que ficou fora do payload OK")

        saved = client.post(
            "/backoffice/stack",
            json={"techs": [{"id": created_tech, "name": "Tech do smoke", "ring": "assess", "quadrant": "tools"}]},
        )
        assert_status(saved, 200, "salvar tech")
        assert len(client.get("/backoffice/stack").json()["techs"]) == tech_count + 1

        # 3) Seeder idempotente e não reverte edição humana.
        #
        # O documento tem que vir de um ARQUIVO que existe em seed_data hoje,
        # não de um `select ... limit 1` na tabela. Linha marcada como semente
        # cujo arquivo de origem foi apagado continua no banco (o seeder não
        # remove órfã), e o reseed jamais a restaura — o teste então falhava ou
        # passava conforme a linha que o `limit 1` sorteasse. Foi o que
        # aconteceu quando `company__company.md` saiu de seed_data e a linha
        # ficou.
        seed_dir = Path(seed_knowledge.__file__).resolve().parents[1] / "seed_data" / "knowledge"
        seed_file = next(iter(sorted(seed_dir.glob("*.md"))), None)
        doc = {"path": seed_file.name} if seed_file else None
        if doc:
            marker = "CONTEUDO EDITADO PELO SMOKE"
            with connect() as conn:
                repo.save_doc(conn, doc["path"], marker, None)
            seed_knowledge.main()
            with connect() as conn:
                after_doc = repo.get_doc(conn, doc["path"])
            assert after_doc["content"] == marker, "o seeder reverteu uma edicao feita dentro do produto"
            assert after_doc["seeded"] is False, after_doc
            print("seeder nao reverte edicao humana OK")

            # devolve o documento ao estado de semente
            with connect() as conn:
                conn.execute(
                    "update eg_knowledge_docs set seeded = true where path = %s", (doc["path"],)
                )
            seed_knowledge.main()
            with connect() as conn:
                restored = repo.get_doc(conn, doc["path"])
            assert restored["content"] != marker, "reseed deveria restaurar documento marcado como semente"
            print("reseed restaura documento marcado como semente OK")

        # 4) Engenharia e arquitetura também saíram do disco.
        engineering = client.get("/backoffice/engineering")
        assert_status(engineering, 200, "listar engenharia")
        modules = engineering.json()["modules"]
        assert len(modules) > 0, "nenhum modulo de engenharia veio do banco"
        with_spec = [row for row in modules if row["hasSpec"]]
        assert with_spec, "nenhum modulo com spec"
        detail = client.get(f"/backoffice/engineering/{with_spec[0]['id']}")
        assert_status(detail, 200, "detalhe do modulo")
        assert detail.json()["specContent"], "spec vazia"
        print(
            f"engenharia do Postgres OK — {len(modules)} modulos, "
            f"{len(detail.json()['adrs'])} ADR(s) no primeiro com spec"
        )

        architecture = client.get("/backoffice/architecture")
        assert_status(architecture, 200, "arquitetura")
        assert len(architecture.json()["md"]) > 100, "documento de arquitetura veio vazio ou truncado"
        print(f"arquitetura do Postgres OK — {len(architecture.json()['md'])} chars")

        assert_status(client.get("/backoffice/engineering/modulo-inexistente"), 404, "modulo inexistente")
        assert_status(client.get("/backoffice/engineering/INVALIDO"), 400, "mod_id invalido")
        print("modulo inexistente 404 e id invalido 400 OK")

        # 5) Busca para o copiloto usar como dossiê.
        with connect() as conn:
            found = repo.search_docs(conn, "Bioma", limit=5)
        print(f"busca em documentos OK — {len(found)} resultado(s) para 'Bioma'")
    finally:
        with connect() as conn:
            conn.execute("delete from eg_ideas where slug = %s", (created_slug,))
            conn.execute("delete from eg_stack_techs where slug = %s", (created_tech,))
    print("limpeza OK — smoke_knowledge_base passou")


if __name__ == "__main__":
    main()
