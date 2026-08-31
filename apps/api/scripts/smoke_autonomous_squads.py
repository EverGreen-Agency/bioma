"""Smoke dos Squads Autônomos: prévia honesta sem chave, execução live mockada
(sem rede) com tokens/custo reais do uso retornado, e persistência/FinOps em
workspace isolado (self-clean).
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

api_path = Path(__file__).resolve().parent.parent
worker_path = api_path.parent / "worker"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

import httpx  # noqa: E402

from bioma_api.db import connect  # noqa: E402
from bioma_api.repositories import squads as squads_repo  # noqa: E402
from bioma_worker.squad_runner import execute_squad_pipeline  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace  # noqa: E402


def mock_transport(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    schema_name = payload["text"]["format"]["name"]
    if schema_name == "bioma_squad_oferta":
        output = {
            "headline": "Headline mockada",
            "mecanismo_unico": "Mecanismo mockado",
            "bonus_stack": ["Bônus mockado"],
            "garantia": "Garantia mockada",
            "recomendacao_regua": "Recomendação mockada",
        }
    elif schema_name == "bioma_squad_demanda":
        output = {
            "estrutura_campanha": "Campanha mockada",
            "publicos_alvo": ["Público mockado"],
            "variacoes_ads": [{"hook": "Gancho mockado", "format": "video"}],
            "orcamento_sugerido_diario_cents": 12345,
        }
    else:
        output = {
            "script_fechamento": "Script mockado",
            "sequencia_whatsapp": [{"dia": 1, "mensagem": "Mensagem mockada"}],
            "quebra_objecoes": {"esta_caro": "Resposta mockada", "preciso_pensar": "Resposta mockada"},
        }
    return httpx.Response(
        200,
        json={
            "id": "resp_smoke",
            "model": "gpt-smoke",
            "output_text": json.dumps(output),
            "usage": {"input_tokens": 900, "output_tokens": 300, "total_tokens": 1200},
        },
    )


def main() -> None:
    print("Testing Autonomous Squads (Oferta, Demanda, Conversão) & FinOps Token Tracking...")

    # 1. Prévia honesta: sem OPENAI_API_KEY, zero tokens e zero custo (nunca números fabricados).
    preview_settings = SimpleNamespace(openai_api_key=None)
    for pilar in ("oferta", "demanda", "conversao"):
        result = execute_squad_pipeline(pilar, f"Squad {pilar}", {"objective": "smoke"}, preview_settings)
        assert result["token_usage"] == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, result
        assert result["estimated_cost_cents"] == 0, result
        assert result["output_data"], "prévia local não deveria retornar output vazio"
    print("[OK] prévia local honesta (sem chave) — zero tokens/custo nos 3 pilares")

    # 2. Execução live mockada: tokens e custo reais vêm do usage retornado, não de constantes fixas.
    live_settings = SimpleNamespace(openai_api_key="smoke-key", openai_model="gpt-smoke", openai_request_timeout_seconds=5)
    mocked_client = httpx.Client(transport=httpx.MockTransport(mock_transport), base_url="https://api.openai.com")
    try:
        res_oferta = execute_squad_pipeline("oferta", "Squad de Revisão de Oferta", {}, live_settings, mocked_client)
        assert res_oferta["output_data"]["headline"] == "Headline mockada"
        assert res_oferta["token_usage"] == {"prompt_tokens": 900, "completion_tokens": 300, "total_tokens": 1200}
        assert res_oferta["estimated_cost_cents"] == 1  # max(1, int(1200/1000*1.5)) = 1

        res_demanda = execute_squad_pipeline("demanda", "Squad de Mídia Paga e Growth", {}, live_settings, mocked_client)
        assert res_demanda["output_data"]["orcamento_sugerido_diario_cents"] == 12345
        assert res_demanda["token_usage"]["total_tokens"] == 1200

        res_conversao = execute_squad_pipeline("conversao", "Squad de Script e Conversão CRM", {}, live_settings, mocked_client)
        assert res_conversao["output_data"]["sequencia_whatsapp"][0]["dia"] == 1
    finally:
        mocked_client.close()
    print("[OK] execução live mockada — schema por pilar + tokens/custo reais do usage")

    # 3. Persistência + agregação FinOps em workspace isolado (self-clean).
    workspace = create_smoke_workspace("AutonomousSquads")
    try:
        with connect() as conn:
            squad_def = squads_repo.upsert_squad_definition(
                conn,
                workspace.workspace_id,
                {
                    "pilar": "oferta",
                    "squad_slug": "squad_oferta_master",
                    "squad_name": "Squad Especialista em Oferta Irresistível",
                    "description": "Squad de agentes autônomos focado em otimização de gargalo de Oferta.",
                    "agents_config": [{"role": "Copywriter"}, {"role": "Pricing Strategist"}],
                    "status": "active",
                },
            )
            assert squad_def["squad_slug"] == "squad_oferta_master"

            exec_row = squads_repo.create_execution(
                conn,
                workspace.workspace_id,
                {
                    "squad_id": squad_def["id"],
                    "pilar": "oferta",
                    "squad_name": "Squad Especialista em Oferta Irresistível",
                    "triggered_by": "smoke_test@evergreen.com",
                    "status": "completed",
                    "input_data": {},
                    "output_data": res_oferta["output_data"],
                    "token_usage": res_oferta["token_usage"],
                    "estimated_cost_cents": res_oferta["estimated_cost_cents"],
                    "execution_logs": res_oferta["execution_logs"],
                    "completed_at": res_oferta["completed_at"],
                },
            )
            assert exec_row["estimated_cost_cents"] == 1

            finops = squads_repo.get_finops_summary(conn, workspace.workspace_id)
            assert finops["total_tokens"] == 1200
            assert finops["total_cost_cents"] == 1
        print(f"[OK] persistência + FinOps isolados: {finops['total_tokens']} tokens, {finops['total_cost_cents']} centavos")
    finally:
        cleanup_smoke_data([workspace.organization_id], [])

    print("\nAUTONOMOUS SQUADS & FINOPS SMOKE TEST OK!")


if __name__ == "__main__":
    main()
