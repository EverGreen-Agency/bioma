"""Smoke da visibilidade de tarefa para o cliente, contra o Postgres real.

Contexto: o board de tarefas do cliente é o mesmo lugar onde entra tanto entrega
contratada quanto trabalho interno de plataforma. Sem controle de visibilidade,
o cliente veria o trabalho interno.

Valida:
- tarefa nasce visível (preserva o comportamento anterior — nada some sozinho);
- marcada como interna, SOME da listagem do usuário do cliente;
- continua visível para a EG;
- o filtro é do backend: a tarefa interna não viaja no payload do cliente.
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
CLIENT_EMAIL = "smoke-visibility-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


# Decisao 13: tarefa de CLIENTE exige projeto, e o workspace de smoke e de
# cliente. Preenchido em main() com o projeto padrao do workspace.
PROJECT_ID = None


def task_payload(title: str, **extra) -> dict:
    payload = {
        "title": title,
        "description": "smoke",
        "project_id": PROJECT_ID,
        "status": "pending",
        "group_status": "NOT_STARTED",
        "recurrence": "none",
        "custom_fields": [],
        "dependencies": [],
        "subtasks": [],
    }
    payload.update(extra)
    return payload


def main() -> None:
    workspace = create_smoke_workspace("VISIBILITY")
    global PROJECT_ID
    PROJECT_ID = str(workspace.project_id)
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Visibility Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)

    # Limpeza garantida mesmo se a falha acontecer antes do try/finally:
    # sem isto, uma assercao quebrada deixa o workspace na carteira.
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    created = admin.post(
        f"/workspaces/{workspace.workspace_id}/task-lists",
        json={"name": "Smoke visibilidade", "type": "growth"},
    )
    assert_status(created, 201, "criar lista")
    list_id = created.json()["id"]

    task_ids: list[str] = []
    try:
        # 1) Nasce visível — comportamento anterior preservado.
        entrega = admin.post(f"/task-lists/{list_id}/tasks", json=task_payload("Entrega contratada do cliente"))
        assert_status(entrega, 201, "criar entrega")
        assert entrega.json()["client_visible"] is True, entrega.json()
        task_ids.append(entrega.json()["id"])
        print("tarefa nasce visivel ao cliente OK")

        # 2) Tarefa interna de plataforma.
        interna = admin.post(
            f"/task-lists/{list_id}/tasks",
            json=task_payload("Refatorar modulo interno", client_visible=False),
        )
        assert_status(interna, 201, "criar interna")
        assert interna.json()["client_visible"] is False, interna.json()
        interna_id = interna.json()["id"]
        task_ids.append(interna_id)

        # 3) EG ve as duas.
        admin_view = admin.get(f"/task-lists/{list_id}/tasks")
        assert_status(admin_view, 200, "EG lista tarefas")
        admin_titles = {row["title"] for row in admin_view.json()}
        assert "Refatorar modulo interno" in admin_titles, admin_titles
        assert len(admin_view.json()) == 2, admin_view.json()

        # 4) Cliente ve so a entrega — e a interna nao viaja no payload.
        client_view = client_user.get(f"/task-lists/{list_id}/tasks")
        assert_status(client_view, 200, "cliente lista tarefas")
        client_titles = {row["title"] for row in client_view.json()}
        assert "Entrega contratada do cliente" in client_titles, client_titles
        assert "Refatorar modulo interno" not in client_titles, "tarefa interna vazou para o cliente"
        assert interna_id not in {row["id"] for row in client_view.json()}, "id da tarefa interna vazou"
        assert len(client_view.json()) == 1, client_view.json()
        print(f"EG ve 2 tarefas, cliente ve 1 — sem vazamento no payload OK")

        # 5) Alternar a visibilidade funciona nos dois sentidos.
        assert_status(
            admin.patch(f"/tasks/{interna_id}", json={"client_visible": True}), 200, "tornar visivel"
        )
        assert len(client_user.get(f"/task-lists/{list_id}/tasks").json()) == 2, "deveria aparecer apos liberar"
        assert_status(
            admin.patch(f"/tasks/{interna_id}", json={"client_visible": False}), 200, "esconder de novo"
        )
        assert len(client_user.get(f"/task-lists/{list_id}/tasks").json()) == 1, "deveria sumir apos esconder"
        print("alternar visibilidade nos dois sentidos OK")
    finally:
        with connect() as conn:
            for task_id in task_ids:
                conn.execute("delete from eg_tasks where id = %s", (task_id,))
            conn.execute("delete from eg_task_lists where id = %s", (list_id,))
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_task_visibility passou")


if __name__ == "__main__":
    main()
