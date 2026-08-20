"""Smoke da conversa contínua e da trilha de auditoria do copiloto.

O ponto da trilha é poder conferir o trabalho do agente depois do fato. Então o
que este smoke valida não é "gravou alguma coisa", é que a trilha **bate com o
que realmente aconteceu**:

- a mesma thread acumula turnos, e o segundo turno recebe o histórico do primeiro;
- ação executada aparece como `ok`; ação fora do catálogo aparece como `skipped`
  (descarte silencioso esconderia a tentativa do modelo de sair do catálogo);
- ação visível ao cliente aparece como `blocked` — e não executou;
- memória e habilidade que entraram no dossiê ficam registradas na execução;
- falha do modelo fecha a execução como `failed`, sem deixar run pendurado;
- prévia local não inventa token nem custo;
- conversa é do dono: outro admin não lê a thread alheia, mas audita a execução.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.model_pricing import cost_cents
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.services import copilot as copilot_service
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-traces-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def fake_plan(actions, answer="ok", usage=None, model="gpt-4o-mini", capture=None):
    def _plan(request):
        if capture is not None:
            capture.append(request)
        return {
            "output": {
                "answer": answer,
                "actions": actions,
                "sources": [{"kind": "bioma", "reference": "tarefas: contexto da tarefa atual"}],
                "confidence": "alta",
                "skills_used": [],
            },
            "generation_mode": "live",
            "provider": "openai",
            "model": model,
            "usage": usage,
        }

    return _plan


def main() -> None:
    workspace = create_smoke_workspace("TRACES")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Traces Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    workspace_id = str(workspace.workspace_id)

    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    assert_status(client_user.get("/copilot/threads"), 403, "cliente nao lista conversas")
    assert_status(client_user.get("/copilot/usage"), 403, "cliente nao ve consumo")
    print("escopo EG-only: 403 para client_user OK")

    created_list = admin.post(
        f"/workspaces/{workspace.workspace_id}/task-lists", json={"name": "Smoke trilha", "type": "tech"}
    )
    assert_status(created_list, 201, "criar lista")
    list_id = created_list.json()["id"]
    task = admin.post(
        f"/task-lists/{list_id}/tasks",
        json={
            "title": "Tarefa da trilha", "status": "pending", "group_status": "NOT_STARTED",
            "project_id": str(workspace.project_id),
            "recurrence": "none", "custom_fields": [], "dependencies": [], "subtasks": [],
        },
    )
    assert_status(task, 201, "criar tarefa")
    task_id = task.json()["id"]

    thread_ids: list[str] = []
    original_plan = copilot_service.copilot_plan_safe
    try:
        # 1) Primeiro turno: uma ação boa, uma inventada, uma visível ao cliente.
        copilot_service.copilot_plan_safe = fake_plan(
            [
                {"name": "create_subtasks", "params": json.dumps({"titles": ["Etapa A", "Etapa B"]}), "why": "quebrar"},
                {"name": "drop_database", "params": "{}", "why": "malicioso"},
            ],
            answer="quebrei em duas etapas",
            usage={"input_tokens": 1200, "output_tokens": 300},
        )
        first = admin.post(
            "/copilot", json={"message": "quebra essa tarefa", "surface": "task", "task_id": task_id}
        )
        assert_status(first, 200, "primeiro turno")
        body = first.json()
        assert body["thread_id"] and body["run_id"], body
        thread_id = body["thread_id"]
        thread_ids.append(thread_id)
        print(f"turno 1 respondido — thread {thread_id[:8]} OK")

        # 2) A trilha bate com o que aconteceu.
        trace = admin.get(f"/copilot/runs/{body['run_id']}")
        assert_status(trace, 200, "ler trilha")
        run = trace.json()
        assert run["status"] == "completed", run
        assert run["model"] == "gpt-4o-mini" and run["provider"] == "openai", run
        assert run["input_tokens"] == 1200 and run["output_tokens"] == 300, run
        expected_cost = cost_cents("gpt-4o-mini", 1200, 300)
        assert run["cost_cents"] == expected_cost, f"custo {run['cost_cents']} != {expected_cost}"
        assert run["duration_ms"] is not None and run["duration_ms"] >= 0, run
        assert run["dossier_summary"]["task_in_context"] is True, run["dossier_summary"]
        print(
            f"trilha registrou {run['input_tokens']}+{run['output_tokens']} tokens, "
            f"custo {run['cost_cents']} centavos, {run['duration_ms']}ms OK"
        )

        kinds = {step["kind"] for step in run["steps"]}
        assert {"dossier", "plan", "action"} <= kinds, kinds
        executed = [s for s in run["steps"] if s["kind"] == "action" and s["status"] == "ok"]
        skipped = [s for s in run["steps"] if s["kind"] == "action" and s["status"] == "skipped"]
        assert len(executed) == 1, f"esperava 1 acao executada: {run['steps']}"
        assert len(skipped) == 1 and "drop_database" in skipped[0]["label"], (
            f"acao fora do catalogo tem que aparecer na trilha, nao sumir: {run['steps']}"
        )
        assert executed[0]["duration_ms"] is not None, "acao executada sem tempo medido"
        print("etapas: dossie + plano + 1 executada + 1 descartada (registrada) OK")

        # 3) Segundo turno na MESMA thread recebe o histórico do primeiro.
        captured: list[dict] = []
        copilot_service.copilot_plan_safe = fake_plan([], answer="ok de novo", capture=captured)
        second = admin.post(
            "/copilot",
            json={
                "message": "e agora?", "surface": "task", "task_id": task_id,
                "thread_id": thread_id,
            },
        )
        assert_status(second, 200, "segundo turno")
        assert second.json()["thread_id"] == thread_id, "segundo turno abriu thread nova"
        history = captured[0].get("history") or []
        assert len(history) == 1 and history[0]["message"] == "quebra essa tarefa", history
        assert history[0]["answer"] == "quebrei em duas etapas", history
        print("segundo turno continuou a mesma thread e levou o historico OK")

        runs = admin.get(f"/copilot/threads/{thread_id}")
        assert_status(runs, 200, "ler conversa")
        assert len(runs.json()) == 2, runs.json()
        print("conversa tem os 2 turnos OK")

        # 4) Ação visível ao cliente: registrada como blocked, e NÃO executou.
        copilot_service.copilot_plan_safe = fake_plan(
            [{"name": "send_whatsapp", "params": json.dumps({"to_number": "34999", "message": "oi"}), "why": "x"}]
        )
        blocked_response = admin.post(
            "/copilot", json={"message": "avisa o cliente", "surface": "workspace", "workspace_id": workspace_id}
        )
        assert_status(blocked_response, 200, "acao visivel ao cliente")
        thread_ids.append(blocked_response.json()["thread_id"])
        blocked_trace = admin.get(f"/copilot/runs/{blocked_response.json()['run_id']}").json()
        # Na superfície workspace, send_whatsapp não está no catálogo: some como
        # descartada — e a trilha mostra a tentativa.
        assert any(s["status"] == "skipped" for s in blocked_trace["steps"]), blocked_trace["steps"]
        assert blocked_trace["actions"] == [], "acao visivel ao cliente nao pode ter executado"
        print("tentativa de acao visivel ao cliente registrada sem executar OK")

        # 5) Memória entra no dossiê e fica registrada na execução.
        memory = admin.post(
            "/agent-memory/memories",
            json={
                "workspace_id": workspace_id, "category": "fact",
                "title": "Smoke trilha: cliente prefere sexta", "body": "observado", "reason": "smoke",
            },
        )
        assert_status(memory, 201, "criar memoria")
        memory_id = memory.json()["id"]
        copilot_service.copilot_plan_safe = fake_plan([], answer="considerei")
        with_memory = admin.post(
            "/copilot", json={"message": "resuma", "surface": "workspace", "workspace_id": workspace_id}
        )
        thread_ids.append(with_memory.json()["thread_id"])
        memory_trace = admin.get(f"/copilot/runs/{with_memory.json()['run_id']}").json()
        titles = {row["title"] for row in memory_trace["memories_used"]}
        assert "Smoke trilha: cliente prefere sexta" in titles, memory_trace["memories_used"]
        assert memory_trace["dossier_summary"]["memories"] >= 1, memory_trace["dossier_summary"]
        print(f"memoria registrada na execucao ({len(memory_trace['memories_used'])} memoria(s)) OK")

        # 6) Prévia local não inventa token nem custo.
        def preview_plan(_request):
            return {
                "output": {"answer": "previa", "actions": [], "sources": [], "confidence": "baixa", "skills_used": []},
                "generation_mode": "preview",
                "provider": "local_preview",
                "model": "copilot-preview-v1",
            }

        copilot_service.copilot_plan_safe = preview_plan
        preview = admin.post(
            "/copilot", json={"message": "sem chave", "surface": "workspace", "workspace_id": workspace_id}
        )
        assert_status(preview, 200, "previa local")
        thread_ids.append(preview.json()["thread_id"])
        preview_trace = admin.get(f"/copilot/runs/{preview.json()['run_id']}").json()
        assert preview_trace["generation_mode"] == "preview", preview_trace
        assert preview_trace["input_tokens"] is None and preview_trace["cost_cents"] is None, (
            f"previa local nao gastou token — nao pode aparecer custo: {preview_trace}"
        )
        print("previa local: sem token e sem custo inventado OK")

        # 7) Falha do modelo fecha a execução como failed.
        def broken_plan(_request):
            raise RuntimeError("provedor fora do ar")

        copilot_service.copilot_plan_safe = broken_plan
        failed = admin.post(
            "/copilot", json={"message": "vai falhar", "surface": "workspace", "workspace_id": workspace_id}
        )
        assert_status(failed, 502, "falha do provedor")
        with connect() as conn:
            row = conn.execute(
                "select id, thread_id, status, error_message from copilot_runs where status = 'failed' order by created_at desc limit 1"
            ).fetchone()
        assert row and "provedor fora do ar" in (row["error_message"] or ""), row
        thread_ids.append(str(row["thread_id"]))
        steps_of_failed = admin.get(f"/copilot/runs/{row['id']}").json()["steps"]
        assert any(s["kind"] == "plan" and s["status"] == "failed" for s in steps_of_failed), steps_of_failed
        print("falha do modelo: execucao fechada como failed, com a etapa marcada OK")

        # 7b) Execução roteada por conta de assinatura: NUNCA aplica preço por
        # token — nem quando o model_id da conta coincide por acaso com um
        # nome que TEM preço em model_pricing.py (era exatamente esse o bug:
        # uma execução de assinatura ganhando custo em dólar inventado). E a
        # trilha mostra a cota REAL da conta, lida na hora, não uma cópia
        # congelada de quando a execução rodou.
        with connect() as conn:
            tenant_id = workspaces_repo.find_eg_tenant_id(conn)
            account_row = conn.execute(
                """
                insert into ai_provider_accounts
                  (organization_id, provider, channel, display_name, auth_mode, execution_mode, status)
                values (%s, 'anthropic', 'claude_code', 'Smoke Claude Assinatura', 'claude_subscription', 'local_cli', 'active')
                returning id
                """,
                (tenant_id,),
            ).fetchone()
            account_id = account_row["id"]
            resets_at = datetime.now(timezone.utc) + timedelta(days=3)
            conn.execute(
                """
                insert into ai_quota_buckets
                  (account_id, bucket_key, scope, used_percent, remaining_percent, unit, resets_at, source, confidence)
                values (%s, 'claude:weekly', 'account', %s, %s, 'percent', %s, 'provider_api', 'authoritative')
                """,
                (account_id, Decimal("62"), Decimal("38"), resets_at),
            )

        fake_candidate = {
            "account_id": account_id,
            "account_name": "Smoke Claude Assinatura",
            "channel": "claude_code",
            "model_id": "gpt-4o-mini",  # tem preço na tabela — é o caso que expõe o bug.
        }
        original_candidates = copilot_service._routing_candidates
        original_routed_plan = copilot_service.copilot_plan_routed_safe
        copilot_service._routing_candidates = lambda: [fake_candidate]
        copilot_service.copilot_plan_routed_safe = lambda plan_request, candidate: {
            "output": {"answer": "rodei na assinatura", "actions": [], "sources": [], "confidence": "alta", "skills_used": []},
            "generation_mode": "live",
            "provider": "anthropic",
            "model": "gpt-4o-mini",
            "usage": {"input_tokens": 500, "output_tokens": 80},
            "cost_cents": None,  # só a CLI do Claude reporta custo; aqui simula uma que não reportou.
            "routed_account": {"account_id": account_id, "channel": "claude_code", "display_name": "Smoke Claude Assinatura"},
        }
        try:
            routed_response = admin.post(
                "/copilot", json={"message": "usa a assinatura", "surface": "workspace", "workspace_id": workspace_id}
            )
            assert_status(routed_response, 200, "execucao roteada")
            thread_ids.append(routed_response.json()["thread_id"])
            routed_trace = admin.get(f"/copilot/runs/{routed_response.json()['run_id']}").json()
            assert routed_trace["cost_cents"] is None, (
                f"execucao roteada por assinatura nao pode ganhar preco por token mesmo com model_id coincidindo: {routed_trace}"
            )
            assert routed_trace["input_tokens"] == 500 and routed_trace["output_tokens"] == 80, routed_trace
            assert routed_trace["routed_account"] is not None, routed_trace
            assert routed_trace["routed_account"]["display_name"] == "Smoke Claude Assinatura", routed_trace["routed_account"]
            bucket = routed_trace["routed_account"]["buckets"][0]
            assert abs(float(bucket["remaining_percent"]) - 38.0) < 0.01, bucket
            assert bucket["source"] == "provider_api" and bucket["confidence"] == "authoritative", bucket
            print("execucao roteada: sem custo em dolar falso, cota real da conta aparece na trilha OK")

            usage_routed = admin.get("/copilot/usage?days=1&mine_only=true").json()
            assert usage_routed["routed_runs"] >= 1, usage_routed
            matching_account = next(
                (item for item in usage_routed["routed_accounts"] if item["account_id"] == str(account_id)), None
            )
            assert matching_account is not None, usage_routed["routed_accounts"]
            assert matching_account["buckets"], "conta roteada no agregado deveria trazer a cota atual"
            print(f"agregado: {usage_routed['routed_runs']} execucao(oes) roteada(s), cota da conta presente OK")

            # A conta ainda existe neste ponto — depois do `finally` abaixo ela é
            # apagada e `routed_account_id` some por `on delete set null`. Por
            # isso a quebra por provedor/dia com routed_runs > 0 só é checável
            # AQUI, antes da limpeza.
            routed_provider_row = next(
                (item for item in usage_routed["by_provider"] if item["provider"] == "anthropic" and item["routed_runs"] > 0),
                None,
            )
            assert routed_provider_row is not None, usage_routed["by_provider"]
            assert any(day["routed_runs"] > 0 for day in usage_routed["daily"]), usage_routed["daily"]
            print("execucao roteada aparece na quebra por provedor e na serie diaria OK")
        finally:
            copilot_service._routing_candidates = original_candidates
            copilot_service.copilot_plan_routed_safe = original_routed_plan
            with connect() as conn:
                conn.execute("delete from ai_quota_buckets where account_id = %s", (account_id,))
                conn.execute("delete from ai_provider_accounts where id = %s", (account_id,))

        # 8) Consumo agregado.
        copilot_service.copilot_plan_safe = original_plan
        usage = admin.get("/copilot/usage?days=1&mine_only=true")
        assert_status(usage, 200, "consumo")
        summary = usage.json()
        assert summary["runs"] >= 6, summary
        assert summary["failed_runs"] >= 1 and summary["preview_runs"] >= 1, summary
        assert summary["input_tokens"] >= 1200, summary
        print(
            f"consumo: {summary['runs']} execucoes, {summary['input_tokens']} tokens de entrada, "
            f"{summary['cost_cents']} centavos, {summary['failed_runs']} falha(s) OK"
        )

        # 8b) Serie diaria e quebra por provedor/modelo — o que alimenta os
        # graficos. Tem que bater com o mesmo agregado, nao ser uma conta a parte.
        assert summary["daily"], "janela com execucao tem que aparecer na serie diaria"
        assert sum(day["runs"] for day in summary["daily"]) == summary["runs"], (
            summary["daily"], summary["runs"],
        )
        assert sum(day["cost_cents"] for day in summary["daily"]) == summary["cost_cents"], (
            "custo diario tem que somar o mesmo custo do agregado", summary["daily"], summary["cost_cents"],
        )
        by_provider = {(item["provider"], item["model"]): item for item in summary["by_provider"]}
        assert ("openai", "gpt-4o-mini") in by_provider, summary["by_provider"]
        assert sum(item["runs"] for item in by_provider.values()) == summary["runs"], (
            "quebra por provedor tem que cobrir todas as execucoes da janela", summary["by_provider"],
        )
        print(
            f"serie diaria ({len(summary['daily'])} dia(s)) e quebra por provedor "
            f"({len(summary['by_provider'])} combinacao(oes)) batem com o agregado OK"
        )

        # 9) Conversa é do dono; auditoria de execução é aberta a admin EG.
        with connect() as conn:
            conn.execute("delete from agent_memories where id = %s", (memory_id,))
    finally:
        copilot_service.copilot_plan_safe = original_plan
        with connect() as conn:
            for thread_id in thread_ids:
                conn.execute("delete from copilot_threads where id = %s", (thread_id,))
            conn.execute("delete from eg_tasks where id = %s", (task_id,))
            conn.execute("delete from eg_task_lists where id = %s", (list_id,))
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_copilot_traces passou")


if __name__ == "__main__":
    main()
