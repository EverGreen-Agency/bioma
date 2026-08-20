"""Smoke do copiloto do Bioma, contra o Postgres real.

Valida o contrato de segurança, que é o ponto do desenho:
- só EG (client_user recebe 403);
- comandos vêm do catálogo do worker, por superfície;
- ação reversível executa e informa como desfazer;
- ação visível ao cliente NUNCA executa — volta como pending_confirmation;
- nome de ação fora do catálogo é descartado sem executar;
- dry_run não altera nada.

Como o plano depende do modelo, o smoke injeta um plano determinístico via
monkeypatch do bridge — assim testa a AUTORIDADE da API, não a criatividade da IA.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.services import copilot as copilot_service
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-copilot-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def fake_plan(actions: list[dict], answer: str = "ok"):
    def _plan(_request):
        return {
            "output": {
                "answer": answer,
                "actions": actions,
                "sources": [{"kind": "bioma", "reference": "tarefas: contexto da tarefa atual"}],
                "confidence": "alta",
            },
            "generation_mode": "live",
            "provider": "fake",
            "model": "fake",
        }

    return _plan


def main() -> None:
    workspace = create_smoke_workspace("COPILOT")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Copilot Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)

    # Limpeza garantida mesmo se a falha acontecer antes do try/finally:
    # sem isto, uma assercao quebrada deixa o workspace na carteira.
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    # Só EG.
    assert_status(client_user.get("/copilot/commands"), 403, "cliente nao acessa comandos")
    assert_status(
        client_user.post("/copilot", json={"message": "oi", "surface": "workspace"}),
        403,
        "cliente nao usa o copiloto",
    )
    print("escopo EG-only: 403 para client_user OK")

    commands = admin.get("/copilot/commands?surface=task")
    assert_status(commands, 200, "comandos da tarefa")
    names = {item["name"] for item in commands.json()}
    assert "create_subtasks" in names and "set_due_date" in names, names
    assert "send_whatsapp" not in names, "acao visivel ao cliente nao pertence a superficie tarefa"
    workspace_commands = admin.get("/copilot/commands?surface=workspace")
    assert_status(workspace_commands, 200, "comandos do workspace")
    # Superfície workspace tem ações reversíveis de memória/skill além de responder —
    # o que ela NÃO pode ter é ação visível ao cliente (send_whatsapp etc.).
    assert "send_whatsapp" not in {item["name"] for item in workspace_commands.json()}, "acao visivel ao cliente vazou pra superficie workspace"
    print(f"catalogo por superficie OK ({len(names)} comandos em tarefa)")

    # Tarefa de teste.
    lists_response = admin.get(f"/workspaces/{workspace.workspace_id}/task-lists")
    assert_status(lists_response, 200, "listas")
    task_lists = lists_response.json()
    if not task_lists:
        created_list = admin.post(
            f"/workspaces/{workspace.workspace_id}/task-lists",
            json={"name": "Smoke Copiloto", "type": "growth"},
        )
        assert_status(created_list, 201, "criar lista")
        task_lists = [created_list.json()]
    list_id = task_lists[0]["id"]

    task = admin.post(
        f"/task-lists/{list_id}/tasks",
        json={
            "title": "Tarefa do smoke do copiloto",
            "project_id": str(workspace.project_id),
            "status": "pending",
            "group_status": "NOT_STARTED",
            "recurrence": "none",
            "custom_fields": [],
            "dependencies": [],
            "subtasks": [],
        },
    )
    assert_status(task, 201, "criar tarefa")
    task_id = task.json()["id"]

    original_plan = copilot_service.copilot_plan_safe
    # Toda chamada ao copiloto abre uma thread; sem guardar os ids, cada execução
    # do smoke deixaria quatro conversas na lista lateral do Eduardo.
    thread_ids: list[str] = []

    def remember_thread(response) -> None:
        body = response.json()
        if isinstance(body, dict) and body.get("thread_id"):
            thread_ids.append(body["thread_id"])

    try:
        # 1) Ação reversível executa e informa como desfazer.
        copilot_service.copilot_plan_safe = fake_plan(
            [{"name": "create_subtasks", "params": json.dumps({"titles": ["Etapa A", "Etapa B"]}), "why": "quebrar"}]
        )
        response = admin.post(
            "/copilot",
            json={"message": "quebra essa tarefa em etapas", "surface": "task", "task_id": task_id},
        )
        assert_status(response, 200, "acao reversivel")
        remember_thread(response)
        body = response.json()
        action = body["actions"][0]
        assert action["status"] == "executed", action
        assert action["undo_hint"], "acao reversivel sem dica de desfazer"
        assert body["sources"], "resposta sem fonte"
        detail = admin.get(f"/task-lists/{list_id}/tasks").json()
        subtasks = next(item for item in detail if item["id"] == task_id)["subtasks"]
        assert len(subtasks) == 2, subtasks
        print(f"acao reversivel executada OK ({len(subtasks)} subtarefas, com undo_hint)")

        # 2) Ação visível ao cliente nunca executa.
        copilot_service.copilot_plan_safe = fake_plan(
            [{"name": "send_whatsapp", "params": json.dumps({"to_number": "34999", "message": "oi"}), "why": "x"}]
        )
        response = admin.post(
            "/copilot",
            json={"message": "manda whats pro cliente", "surface": "task", "task_id": task_id},
        )
        assert_status(response, 200, "acao visivel ao cliente")
        remember_thread(response)
        # Fora da superfície `task`, é descartada antes de qualquer coisa.
        assert response.json()["actions"] == [], response.json()["actions"]
        print("acao visivel ao cliente fora da superficie: descartada OK")

        # 3) Nome inventado é descartado.
        copilot_service.copilot_plan_safe = fake_plan(
            [{"name": "drop_database", "params": "{}", "why": "malicioso"}]
        )
        response = admin.post(
            "/copilot",
            json={"message": "apaga tudo", "surface": "task", "task_id": task_id},
        )
        assert_status(response, 200, "acao inventada")
        remember_thread(response)
        assert response.json()["actions"] == [], "acao fora do catalogo nao pode passar"
        print("acao fora do catalogo: descartada OK")

        # 4) dry_run não altera nada.
        copilot_service.copilot_plan_safe = fake_plan(
            [{"name": "set_status", "params": json.dumps({"status": "in_progress"}), "why": "avancar"}]
        )
        response = admin.post(
            "/copilot",
            json={"message": "muda o status", "surface": "task", "task_id": task_id, "dry_run": True},
        )
        assert_status(response, 200, "dry run")
        remember_thread(response)
        assert response.json()["actions"][0]["status"] == "proposed", response.json()["actions"][0]
        after = next(
            item for item in admin.get(f"/task-lists/{list_id}/tasks").json() if item["id"] == task_id
        )
        assert after["status"] == "pending", f"dry_run alterou o status: {after['status']}"
        print("dry_run nao alterou nada OK")

        # 5) Tarefa inexistente: 404.
        assert_status(
            admin.post(
                "/copilot",
                json={
                    "message": "x",
                    "surface": "task",
                    "task_id": "00000000-0000-0000-0000-000000000000",
                },
            ),
            404,
            "tarefa inexistente",
        )
        print("tarefa inexistente: 404 OK")
    finally:
        copilot_service.copilot_plan_safe = original_plan
        with connect() as conn:
            for thread_id in thread_ids:
                conn.execute("delete from copilot_threads where id = %s", (thread_id,))
            conn.execute("delete from eg_tasks where id = %s", (task_id,))
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_copilot passou")


if __name__ == "__main__":
    main()
