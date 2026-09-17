"""Smoke dos artefatos versionados com procedência (decisão 8).

O que a decisão promete e este smoke fixa:

- o material que a conversa produz vira objeto com nome, versão e elo de volta
  para a execução que o gerou;
- **nova versão nunca sobrescreve** — v1 continua legível depois da v2, que é
  o que separa iterar de regerar;
- `artifacts.content` acompanha a versão corrente, para as telas antigas
  continuarem funcionando sem saber que versionamento existe;
- apagar a conversa NÃO apaga o material (o elo cai, a peça fica);
- artefato pertence a um workspace e não vaza para outro.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
OUTSIDER_EMAIL = "smoke-artifacts-outsider@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    workspace = create_smoke_workspace("ARTIFACTS")
    other = create_smoke_workspace("ARTIFACTSOUT")
    outsider_id = upsert_smoke_user(OUTSIDER_EMAIL, "Smoke Outsider", PASSWORD)
    grant_client_user(other, outsider_id)
    atexit.register(
        cleanup_smoke_data, [workspace.organization_id, other.organization_id], [OUTSIDER_EMAIL]
    )

    thread_id = None
    try:
        admin = TestClient(app)
        assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login")

        # Uma thread de copiloto real, para o artefato ter de onde vir.
        with connect() as conn:
            user_row = conn.execute("select id from users where lower(email) = %s", (ADMIN_EMAIL,)).fetchone()
            thread_id = conn.execute(
                """
                insert into copilot_threads (user_id, surface, workspace_id, title)
                values (%s, 'smoke', %s, 'Conversa do smoke')
                returning id
                """,
                (user_row["id"], workspace.workspace_id),
            ).fetchone()["id"]

        # ---------------------------------------------------------------- 1
        response = admin.post(
            f"/workspaces/{workspace.workspace_id}/studio",
            json={
                "title": "Roteiro — lançamento",
                "kind": "roteiro",
                "content": "Gancho A",
                "thread_id": str(thread_id),
                "change_note": "primeira geração",
            },
        )
        assert_status(response, 201, "criar artefato")
        artifact = response.json()
        artifact_id = artifact["id"]
        if artifact["current_version"] != 1 or artifact["versions_total"] != 1:
            raise AssertionError(f"artefato não nasceu na v1: {artifact}")
        if artifact["thread_id"] != str(thread_id):
            raise AssertionError("procedência (thread) não foi guardada")
        print("ok: artefato nasce na v1 com elo para a conversa")

        # ---------------------------------------------------------------- 2
        response = admin.post(
            f"/artifacts/{artifact_id}/versions",
            json={"title": "Roteiro — lançamento", "content": "Gancho B", "change_note": "ajustei o gancho"},
        )
        assert_status(response, 201, "criar v2")
        detail = response.json()
        if detail["current_version"] != 2:
            raise AssertionError(f"versão corrente não avançou: {detail['current_version']}")
        if detail["content"] != "Gancho B":
            raise AssertionError("conteúdo corrente não acompanhou a nova versão")

        versions = {item["version"]: item for item in detail["versions"]}
        if versions[1]["content"] != "Gancho A":
            raise AssertionError("a v1 foi sobrescrita — versionamento não está protegendo nada")
        if versions[2]["change_note"] != "ajustei o gancho":
            raise AssertionError("o motivo da mudança não foi guardado")
        print("ok: v2 criada, v1 preservada e legível, motivo registrado")

        # ---------------------------------------------------------------- 3
        # As telas antigas leem `artifacts.content` — precisa ser a corrente.
        with connect() as conn:
            row = conn.execute("select content, current_version from artifacts where id = %s", (artifact_id,)).fetchone()
        if row["content"] != "Gancho B" or row["current_version"] != 2:
            raise AssertionError(f"tabela base não acompanhou a versão corrente: {dict(row)}")
        print("ok: artifacts.content é sempre a versão corrente (telas antigas seguem funcionando)")

        # ---------------------------------------------------------------- 4
        assert_status(
            admin.patch(f"/artifacts/{artifact_id}/status", json={"status": "approved"}),
            200,
            "aprovar artefato",
        )
        print("ok: status muda (rascunho para aprovado)")

        # ---------------------------------------------------------------- 5
        # Apagar a conversa não pode apagar o material.
        with connect() as conn:
            conn.execute("delete from copilot_threads where id = %s", (thread_id,))
        response = admin.get(f"/artifacts/{artifact_id}")
        assert_status(response, 200, "artefato sobrevive à conversa")
        if response.json()["thread_id"] is not None:
            raise AssertionError("o elo deveria ter caído junto com a conversa")
        if response.json()["content"] != "Gancho B":
            raise AssertionError("apagar a conversa levou o material junto — perda de trabalho")
        thread_id = None
        print("ok: apagar a conversa derruba o elo, não o material")

        # ---------------------------------------------------------------- 6
        listing = admin.get(f"/workspaces/{workspace.workspace_id}/studio?kind=roteiro")
        assert_status(listing, 200, "listar por tipo")
        if not any(item["id"] == artifact_id for item in listing.json()):
            raise AssertionError("filtro por tipo não devolveu o artefato")

        kinds = admin.get(f"/workspaces/{workspace.workspace_id}/studio/kinds").json()
        if not any(item["kind"] == "roteiro" for item in kinds):
            raise AssertionError(f"catálogo de tipos não descobriu 'roteiro': {kinds}")
        print("ok: vista filtra por tipo e descobre os tipos existentes")

        # ---------------------------------------------------------------- 7
        # O elo: salvar a resposta de uma execucao como artefato, com a
        # procedencia deduzida pelo servidor.
        with connect() as conn:
            second_thread = conn.execute(
                """
                insert into copilot_threads (user_id, surface, workspace_id, title)
                values (%s, 'smoke', %s, 'Conversa que gera material')
                returning id
                """,
                (user_row["id"], workspace.workspace_id),
            ).fetchone()["id"]
            run_id = conn.execute(
                """
                insert into copilot_runs (thread_id, user_id, surface, workspace_id, message, answer, status)
                values (%s, %s, 'smoke', %s, 'faz um roteiro', 'ROTEIRO GERADO PELO COPILOTO', 'completed')
                returning id
                """,
                (second_thread, user_row["id"], workspace.workspace_id),
            ).fetchone()["id"]

        response = admin.post(
            f"/artifacts/from-run/{run_id}",
            json={"title": "Roteiro vindo da conversa", "kind": "roteiro"},
        )
        assert_status(response, 201, "salvar execucao como artefato")
        from_run = response.json()
        if from_run["content"] != "ROTEIRO GERADO PELO COPILOTO":
            raise AssertionError("a resposta da execucao nao virou o conteudo do artefato")
        if from_run["run_id"] != str(run_id) or from_run["thread_id"] != str(second_thread):
            raise AssertionError(f"procedencia nao foi deduzida da execucao: {from_run}")
        print("ok: resposta do copiloto vira artefato com procedencia deduzida")

        # Salvar de novo apontando o artefato existente vira v2, nao duplicata.
        response = admin.post(
            f"/artifacts/from-run/{run_id}",
            json={
                "title": "Roteiro vindo da conversa",
                "kind": "roteiro",
                "artifact_id": from_run["id"],
                "content": "VERSAO REVISADA",
                "change_note": "regerado",
            },
        )
        assert_status(response, 201, "salvar como nova versao")
        if response.json()["current_version"] != 2:
            raise AssertionError("salvar de novo criou duplicata em vez de versao")
        if response.json()["versions"][-1]["run_id"] != str(run_id):
            raise AssertionError("a v1 perdeu o elo com a execucao")
        print("ok: regerar vira v2 do mesmo artefato, sem perder a v1")

        # ---------------------------------------------------------------- 8
        outsider = TestClient(app)
        assert_status(outsider.post("/auth/login", json={"email": OUTSIDER_EMAIL, "password": PASSWORD}), 200, "login outsider")
        response = outsider.get(f"/artifacts/{artifact_id}")
        if response.status_code not in (403, 404):
            raise AssertionError(f"artefato vazou para outro workspace: {response.status_code}")
        print(f"ok: artefato não vaza entre workspaces ({response.status_code})")

        print("\nSMOKE ARTIFACTS: OK")
    finally:
        with connect() as conn:
            if thread_id:
                conn.execute("delete from copilot_threads where id = %s", (thread_id,))
            conn.execute("delete from copilot_threads where title = 'Conversa que gera material'")
        cleanup_smoke_data([workspace.organization_id, other.organization_id], [OUTSIDER_EMAIL])


if __name__ == "__main__":
    main()
