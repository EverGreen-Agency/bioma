"""Smoke dos planos multi-etapa do copiloto, contra o Postgres real.

Valida o contrato de segurança, que é o ponto do desenho:
- plano nasce pending_approval e NADA executa antes da aprovação;
- ação fora do catálogo nunca vira etapa;
- etapa visível ao cliente nasce `blocked` e continua bloqueada mesmo com o
  plano aprovado — exige confirmação própria;
- aprovar duas vezes é 409 (não reexecuta);
- falha no meio interrompe: o resto vira `skipped`, não executa às cegas;
- só EG.

O planejador é injetado (plano determinístico) para testar a AUTORIDADE da API,
não a criatividade do modelo.
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
from bioma_api.services import copilot_plans as plans_service
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-plans-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def fake_planner(steps, summary="plano de teste", open_questions=None):
    def _plan(_request):
        return {
            "output": {
                "summary": summary,
                "steps": steps,
                "open_questions": open_questions or [],
            },
            "generation_mode": "live",
        }

    return _plan


def main() -> None:
    workspace = create_smoke_workspace("PLANS")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Plans Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)
    # Limpeza garantida mesmo se a falha acontecer antes do try/finally:
    # sem isto, uma assercao quebrada deixa o workspace na carteira.
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    workspace_id = str(workspace.workspace_id)

    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    assert_status(
        client_user.post("/copilot/plans", json={"goal": "qualquer coisa"}),
        403,
        "cliente nao cria plano",
    )
    print("escopo EG-only: 403 para client_user OK")

    plan_ids: list[str] = []
    memory_titles = ["Smoke plano: fato A", "Smoke plano: fato B"]
    original_planner = plans_service.copilot_plan_multistep_safe
    try:
        # 1) Plano com 2 etapas reversiveis + 1 acao inventada (deve sumir).
        plans_service.copilot_plan_multistep_safe = fake_planner(
            [
                {
                    "action": "remember_fact",
                    "label": "Guardar o fato A",
                    "params": json.dumps({"category": "fact", "title": memory_titles[0], "body": "conteudo A"}),
                    "why": "contexto",
                },
                {
                    "action": "remember_fact",
                    "label": "Guardar o fato B",
                    "params": json.dumps({"category": "fact", "title": memory_titles[1], "body": "conteudo B"}),
                    "why": "contexto",
                },
                {"action": "drop_database", "label": "Apagar tudo", "params": "{}", "why": "malicioso"},
            ],
            open_questions=["Qual o orcamento?"],
        )
        created = admin.post("/copilot/plans", json={"goal": "guardar dois fatos", "workspace_id": workspace_id})
        assert_status(created, 201, "criar plano")
        plan = created.json()
        plan_ids.append(plan["id"])
        assert plan["status"] == "pending_approval", plan
        assert len(plan["steps"]) == 2, f"acao fora do catalogo virou etapa: {plan['steps']}"
        assert all(step["status"] == "pending" for step in plan["steps"]), plan["steps"]
        assert plan["open_questions"] == ["Qual o orcamento?"], plan["open_questions"]
        print(f"plano criado OK — {len(plan['steps'])} etapas, acao inventada descartada, {len(plan['open_questions'])} pergunta(s)")

        # 2) Nada executou antes da aprovacao.
        memories = admin.get(f"/agent-memory/memories?workspace_id={workspace_id}").json()
        assert not any(row["title"] in memory_titles for row in memories), "etapa executou antes da aprovacao"
        print("nada executou antes da aprovacao OK")

        # 3) Aprovar executa em ordem.
        approved = admin.post(f"/copilot/plans/{plan['id']}/approve")
        assert_status(approved, 200, "aprovar plano")
        body = approved.json()
        assert body["status"] == "completed", body
        assert all(step["status"] == "executed" for step in body["steps"]), body["steps"]
        assert all(step["undo_hint"] for step in body["steps"]), "etapa executada sem undo_hint"
        memories = admin.get(f"/agent-memory/memories?workspace_id={workspace_id}").json()
        created_titles = {row["title"] for row in memories}
        assert set(memory_titles) <= created_titles, f"etapas nao criaram as memorias: {created_titles}"
        print("aprovacao executou as 2 etapas em ordem, com undo_hint OK")

        # 4) Aprovar de novo: 409.
        assert_status(admin.post(f"/copilot/plans/{plan['id']}/approve"), 409, "aprovar duas vezes")
        print("aprovar duas vezes: 409 OK")

        # 5) Etapa visivel ao cliente nasce blocked e continua blocked.
        plans_service.copilot_plan_multistep_safe = fake_planner(
            [
                {
                    "action": "remember_fact",
                    "label": "Guardar contexto",
                    "params": json.dumps({"category": "fact", "title": "Smoke plano: fato C", "body": "c"}),
                    "why": "x",
                },
                {
                    "action": "send_whatsapp",
                    "label": "Avisar o cliente",
                    "params": json.dumps({"to_number": "34999", "message": "oi"}),
                    "why": "comunicar",
                },
            ]
        )
        created = admin.post("/copilot/plans", json={"goal": "avisar cliente", "workspace_id": workspace_id})
        assert_status(created, 201, "criar plano com acao visivel")
        plan2 = created.json()
        plan_ids.append(plan2["id"])
        memory_titles.append("Smoke plano: fato C")
        assert plan2["requires_confirmation_count"] == 1, plan2
        blocked_step = next(step for step in plan2["steps"] if step["action_name"] == "send_whatsapp")
        assert blocked_step["status"] == "blocked", blocked_step
        print("etapa visivel ao cliente nasce blocked OK")

        approved2 = admin.post(f"/copilot/plans/{plan2['id']}/approve")
        assert_status(approved2, 200, "aprovar plano 2")
        body2 = approved2.json()
        still_blocked = next(step for step in body2["steps"] if step["action_name"] == "send_whatsapp")
        assert still_blocked["status"] == "blocked", "aprovar o plano nao pode desbloquear acao visivel ao cliente"
        assert body2["status"] == "approved", f"plano com etapa pendente nao pode estar completed: {body2['status']}"
        print("plano aprovado NAO desbloqueia acao visivel ao cliente OK")

        # 6) Falha no meio interrompe a sequencia.
        plans_service.copilot_plan_multistep_safe = fake_planner(
            [
                {"action": "remember_fact", "label": "Etapa invalida", "params": json.dumps({"category": "fact"}), "why": "faltam campos"},
                {
                    "action": "remember_fact",
                    "label": "Nao deve executar",
                    "params": json.dumps({"category": "fact", "title": "Smoke plano: NAO DEVE EXISTIR", "body": "x"}),
                    "why": "x",
                },
            ]
        )
        created = admin.post("/copilot/plans", json={"goal": "plano que falha", "workspace_id": workspace_id})
        assert_status(created, 201, "criar plano que falha")
        plan3 = created.json()
        plan_ids.append(plan3["id"])
        approved3 = admin.post(f"/copilot/plans/{plan3['id']}/approve")
        assert_status(approved3, 200, "aprovar plano que falha")
        body3 = approved3.json()
        assert body3["status"] == "failed", body3
        assert body3["steps"][0]["status"] == "failed", body3["steps"]
        assert body3["steps"][1]["status"] == "skipped", "etapa apos falha deveria ser skipped"
        memories = admin.get(f"/agent-memory/memories?workspace_id={workspace_id}").json()
        assert not any(row["title"] == "Smoke plano: NAO DEVE EXISTIR" for row in memories), "executou apos falha"
        print("falha interrompe a sequencia (resto = skipped) OK")

        # 7) Rejeitar plano pendente.
        plans_service.copilot_plan_multistep_safe = fake_planner(
            [{"action": "answer_only", "label": "so responder", "params": "{}", "why": "x"}]
        )
        created = admin.post("/copilot/plans", json={"goal": "plano a rejeitar", "workspace_id": workspace_id})
        plan4 = created.json()
        plan_ids.append(plan4["id"])
        rejected = admin.post(f"/copilot/plans/{plan4['id']}/reject")
        assert_status(rejected, 200, "rejeitar plano")
        assert rejected.json()["status"] == "rejected", rejected.json()
        assert_status(admin.post(f"/copilot/plans/{plan4['id']}/approve"), 409, "aprovar plano rejeitado")
        print("rejeitar plano e recusar aprovacao posterior OK")
    finally:
        plans_service.copilot_plan_multistep_safe = original_planner
        with connect() as conn:
            for plan_id in plan_ids:
                conn.execute("delete from copilot_plans where id = %s", (plan_id,))
            for title in memory_titles:
                conn.execute("delete from agent_memories where title = %s", (title,))
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_copilot_plans passou")


if __name__ == "__main__":
    main()
