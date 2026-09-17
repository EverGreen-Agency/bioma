"""Smoke do fluxo de requisição de melhoria (Caminho B), contra o Postgres real.

Fecha o ciclo desenhado com o Eduardo: o copiloto percebe uma necessidade que o
catálogo não atende → registra com evidência → você revisa → vira TAREFA.

Valida:
- copiloto registra a requisição como pendente (proposed_by NULL = veio do agente);
- converter cria tarefa de verdade e tira da fila (sem duplicar);
- `client_deliverable` decide a visibilidade da tarefa criada — entrega do
  cliente nasce visível no board dele, melhoria interna nasce escondida;
- converter/rejeitar duas vezes é 409;
- só EG.
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
CLIENT_EMAIL = "smoke-improvement-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def fake_plan(actions):
    def _plan(_request):
        return {
            "output": {"answer": "ok", "actions": actions, "sources": [], "confidence": "alta", "skills_used": []},
            "generation_mode": "live",
            "provider": "fake",
            "model": "fake",
        }

    return _plan


def main() -> None:
    workspace = create_smoke_workspace("IMPROVEMENT")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Improvement Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)
    # Limpeza garantida mesmo se a falha acontecer antes do try/finally:
    # sem isto, uma assercao quebrada deixa o workspace na carteira.
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    workspace_id = str(workspace.workspace_id)

    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    assert_status(client_user.get("/improvement-requests"), 403, "cliente nao ve a fila")
    print("escopo EG-only: 403 para client_user OK")

    created = admin.post(
        f"/workspaces/{workspace.workspace_id}/task-lists",
        json={"name": "Smoke melhorias", "type": "tech"},
    )
    assert_status(created, 201, "criar lista")
    list_id = created.json()["id"]

    request_ids: list[str] = []
    task_ids: list[str] = []
    original_plan = copilot_service.copilot_plan_safe
    try:
        # 1) Copiloto registra a necessidade (entrega esperada pelo cliente).
        copilot_service.copilot_plan_safe = fake_plan(
            [
                {
                    "name": "request_improvement",
                    "params": json.dumps(
                        {
                            "title": "Calendario de visitas dos representantes",
                            "need": "Cliente precisa ver visitas agendadas por representante e regiao.",
                            "evidence": "Tentei montar com os widgets atuais; nao ha widget de calendario por responsavel.",
                            "client_deliverable": True,
                        }
                    ),
                    "why": "necessidade levantada na conversa",
                }
            ]
        )
        response = admin.post(
            "/copilot",
            json={"message": "eles precisam ver as visitas", "surface": "workspace", "workspace_id": workspace_id},
        )
        assert_status(response, 200, "copiloto registra melhoria")
        action = response.json()["actions"][0]
        assert action["status"] == "executed", action
        assert "entrega do cliente" in action["detail"], action["detail"]
        print("copiloto registrou a necessidade OK")

        pending = admin.get("/improvement-requests?status=pending").json()
        item = next(row for row in pending if row["title"] == "Calendario de visitas dos representantes")
        request_ids.append(item["id"])
        assert item["proposed_by"] is None, "requisicao do copiloto nao deveria ter autor humano"
        assert item["client_deliverable"] is True, item
        assert item["evidence"], "requisicao sem evidencia perde o valor"
        print("fila mostra a requisicao com evidencia e origem do agente OK")

        # 2) Converter cria tarefa VISIVEL (é entrega esperada pelo cliente).
        converted = admin.post(
            f"/improvement-requests/{item['id']}/convert",
            json={"list_id": list_id, "review_note": "vale fazer"},
        )
        assert_status(converted, 200, "converter em tarefa")
        body = converted.json()
        assert body["status"] == "converted" and body["task_id"], body
        task_ids.append(body["task_id"])

        tasks = admin.get(f"/task-lists/{list_id}/tasks").json()
        task = next(row for row in tasks if row["id"] == body["task_id"])
        assert task["client_visible"] is True, "entrega do cliente deveria nascer visivel"
        assert "Evidência levantada pelo copiloto" in (task["description"] or ""), task["description"]
        client_tasks = client_user.get(f"/task-lists/{list_id}/tasks").json()
        assert any(row["id"] == body["task_id"] for row in client_tasks), "cliente deveria ver a entrega dele"
        print("conversao criou tarefa visivel ao cliente, com a evidencia na descricao OK")

        # 3) Saiu da fila — nao duplica.
        assert not any(row["id"] == item["id"] for row in admin.get("/improvement-requests?status=pending").json()), (
            "requisicao convertida continua na fila — estaria duplicada em dois lugares"
        )
        assert_status(
            admin.post(f"/improvement-requests/{item['id']}/convert", json={"list_id": list_id}),
            409,
            "converter duas vezes",
        )
        print("saiu da fila e converter de novo e 409 OK")

        # 4) Melhoria interna nasce ESCONDIDA do cliente.
        internal = admin.post(
            "/improvement-requests",
            json={
                "title": "Refatorar camada de widgets",
                "need": "Preparar o catalogo para composicao.",
                "workspace_id": workspace_id,
                "client_deliverable": False,
            },
        )
        assert_status(internal, 201, "criar requisicao interna")
        request_ids.append(internal.json()["id"])
        converted_internal = admin.post(
            f"/improvement-requests/{internal.json()['id']}/convert", json={"list_id": list_id}
        )
        assert_status(converted_internal, 200, "converter interna")
        internal_task_id = converted_internal.json()["task_id"]
        task_ids.append(internal_task_id)
        client_tasks = client_user.get(f"/task-lists/{list_id}/tasks").json()
        assert not any(row["id"] == internal_task_id for row in client_tasks), "melhoria interna vazou para o cliente"
        print("melhoria interna nasceu escondida do cliente OK")

        # 5) Rejeitar.
        rejected_request = admin.post(
            "/improvement-requests",
            json={"title": "Ideia a descartar", "need": "nao faz sentido", "workspace_id": workspace_id},
        )
        request_ids.append(rejected_request.json()["id"])
        rejected = admin.post(
            f"/improvement-requests/{rejected_request.json()['id']}/reject", json={"review_note": "fora de escopo"}
        )
        assert_status(rejected, 200, "rejeitar")
        assert rejected.json()["status"] == "rejected", rejected.json()
        assert_status(
            admin.post(f"/improvement-requests/{rejected_request.json()['id']}/reject", json={}),
            409,
            "rejeitar duas vezes",
        )
        print("rejeitar e recusar rejeicao dupla OK")
    finally:
        copilot_service.copilot_plan_safe = original_plan
        with connect() as conn:
            for request_id in request_ids:
                conn.execute("delete from improvement_requests where id = %s", (request_id,))
            for task_id in task_ids:
                conn.execute("delete from eg_tasks where id = %s", (task_id,))
            conn.execute("delete from eg_task_lists where id = %s", (list_id,))
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_improvement_requests passou")


if __name__ == "__main__":
    main()
