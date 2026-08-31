"""Context Engine, Fase 1 — decisão 7.

Percorre o corte vertical inteiro contra Postgres real: criar base → enviar
texto → fragmentar → inspecionar → desativar fragmento → buscar → abrir a
citação na origem.

A asserção que mais importa é a da **citação verificável**: o trecho devolvido
por `/origin` tem que bater exatamente com o conteúdo do fragmento, recortado
do texto de origem pelos offsets guardados. Se isso quebrar, a base passa a
responder sem poder provar de onde tirou — que é pior do que não responder.
"""

import os
from pathlib import Path
import sys
from urllib.parse import urlparse

from cryptography.fernet import Fernet


os.environ.setdefault("SECRET_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))

SMOKE_DATABASE_URL = os.environ.get("BIOMA_SMOKE_DATABASE_URL")
if not SMOKE_DATABASE_URL:
    raise RuntimeError("Defina BIOMA_SMOKE_DATABASE_URL para executar smoke_knowledge.py fora do banco operacional.")
smoke_database_name = urlparse(SMOKE_DATABASE_URL).path.lstrip("/").lower()
if not smoke_database_name.endswith(("_test", "_smoke")):
    raise RuntimeError("BIOMA_SMOKE_DATABASE_URL deve apontar para um banco com sufixo _test ou _smoke.")
os.environ["DATABASE_URL"] = SMOKE_DATABASE_URL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from bioma_api.main import app  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace, upsert_smoke_user  # noqa: E402


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"

DOCUMENTO = """# Politica de atendimento

Regra geral do atendimento da agencia.

## Prazo de resposta

Toda mensagem de cliente e respondida em ate quatro horas uteis.
Fora do horario comercial, no primeiro expediente seguinte.

## Escalonamento

### Quando escalar

Escale para o responsavel quando o cliente pedir desconto contratual.
"""


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    assert_status(client.post("/auth/login", json={"email": email, "password": PASSWORD}), 200, f"login {email}")


def main() -> None:
    workspace = create_smoke_workspace("KNOWLEDGE")
    outro = create_smoke_workspace("KNOWLEDGE Outro")
    upsert_smoke_user(ADMIN_EMAIL, "Eduardo", PASSWORD)

    try:
        with TestClient(app) as admin:
            login(admin, ADMIN_EMAIL)
            base_url = f"/workspaces/{workspace.workspace_id}/knowledge"

            # --- criar base --------------------------------------------------
            base = admin.post(base_url + "/bases", json={"name": "Processos da EG"})
            assert_status(base, 201, "criar base")
            base_id = base.json()["id"]

            assert_status(
                admin.post(base_url + "/bases", json={"name": "Processos da EG"}),
                422,
                "nome repetido no mesmo workspace e recusado",
            )
            print("criar base e recusar nome repetido OK")

            # --- enviar documento --------------------------------------------
            documento = admin.post(
                f"{base_url}/bases/{base_id}/documents",
                json={"title": "Politica de atendimento", "content": DOCUMENTO},
            )
            assert_status(documento, 201, "enviar documento")
            corpo = documento.json()
            assert corpo["status"] == "indexed", corpo
            assert corpo["chunks_total"] > 1, f"o documento tem secoes; deveria virar varios fragmentos: {corpo}"
            document_id = corpo["id"]
            print(f"documento indexado em {corpo['chunks_total']} fragmento(s) OK")

            # Texto sem nada aproveitavel NAO some: fica visivel com o motivo.
            vazio = admin.post(
                f"{base_url}/bases/{base_id}/documents",
                json={"title": "So espaco", "content": "   \n\n   "},
            )
            assert_status(vazio, 201, "documento vazio ainda e criado")
            assert vazio.json()["status"] == "failed", vazio.json()
            assert vazio.json()["failure_reason"], "falha sem motivo nao ajuda ninguem"
            print("documento sem conteudo fica visivel com o motivo OK")

            # --- inspecionar --------------------------------------------------
            fragmentos = admin.get(f"{base_url}/documents/{document_id}/chunks")
            assert_status(fragmentos, 200, "listar fragmentos")
            lista = fragmentos.json()
            assert [f["position"] for f in lista] == list(range(len(lista))), lista
            fundo = next(f for f in lista if "desconto contratual" in f["content"])
            assert fundo["heading_path"] == ["Politica de atendimento", "Escalonamento", "Quando escalar"], fundo
            print("inspecao mostra posicao e trilha de titulos OK")

            # --- buscar --------------------------------------------------------
            busca = admin.get(f"{base_url}/search", params={"q": "prazo resposta"})
            assert_status(busca, 200, "buscar")
            resultado = busca.json()
            assert resultado["mode_actually_used"] == "lexical", resultado
            assert resultado["capabilities"]["dense"] == "unavailable", resultado
            assert resultado["hits"], "a busca deveria achar o trecho de prazo"
            achado = resultado["hits"][0]
            print(f"busca lexical achou {len(resultado['hits'])} trecho(s), declarando o modo OK")

            # --- citacao verificavel -------------------------------------------
            origem = admin.get(f"{base_url}/chunks/{achado['chunk_id']}/origin")
            assert_status(origem, 200, "abrir a citacao na origem")
            citacao = origem.json()
            assert citacao["content"] == achado["content"], (
                "o trecho da origem TEM que bater com o do resultado; se nao bate, "
                "a citacao nao prova nada"
            )
            assert citacao["char_start"] == achado["char_start"], citacao
            # O recorte veio do texto de origem: o que vem antes/depois nao pode
            # ser inventado, e a juncao tem que existir no documento enviado.
            assert citacao["before"] + citacao["content"] + citacao["after"] in DOCUMENTO, citacao
            print("citacao bate com o texto de origem, com contexto ao redor OK")

            # --- desativar fragmento -------------------------------------------
            alvo = achado["chunk_id"]
            assert_status(
                admin.patch(f"{base_url}/chunks/{alvo}", json={"is_active": False}),
                200,
                "desativar fragmento",
            )
            depois = admin.get(f"{base_url}/search", params={"q": "prazo resposta"}).json()
            assert all(hit["chunk_id"] != alvo for hit in depois["hits"]), (
                "fragmento desativado nao pode voltar na busca"
            )

            # Desativar NAO apaga: ele continua inspecionavel, que e o ponto.
            ainda_la = admin.get(f"{base_url}/documents/{document_id}/chunks").json()
            desativado = next(f for f in ainda_la if f["id"] == alvo)
            assert desativado["is_active"] is False, desativado
            print("desativar tira da busca e MANTEM inspecionavel OK")

            assert_status(
                admin.patch(f"{base_url}/chunks/{alvo}", json={"is_active": True}),
                200,
                "reativar fragmento",
            )

            # --- isolamento -----------------------------------------------------
            alheio = f"/workspaces/{outro.workspace_id}/knowledge"
            assert_status(
                admin.get(f"{alheio}/bases/{base_id}/documents"),
                404,
                "base de outro workspace nao e alcancavel",
            )
            assert_status(
                admin.get(f"{alheio}/chunks/{alvo}/origin"),
                404,
                "fragmento de outro workspace nao e alcancavel",
            )
            vazia = admin.get(f"{alheio}/search", params={"q": "prazo resposta"}).json()
            assert vazia["hits"] == [], "a busca nao pode atravessar workspace"
            print("isolamento entre workspaces OK")

        print("limpeza OK - smoke_knowledge passou")
    finally:
        cleanup_smoke_data([workspace.organization_id, outro.organization_id], [])


if __name__ == "__main__":
    main()
