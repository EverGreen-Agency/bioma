"""Smoke do Brand Book versionado, Calendário Editorial e do servidor MCP.

O servidor MCP agora exige service_token + um workspace fixo configurado por
instância (fix de segurança: antes aceitava qualquer workspace_id sem
autenticação nenhuma). Testa negação sem token, negação para um workspace
diferente do configurado (mesmo de outro cliente da mesma agência) e sucesso
dentro do workspace autorizado — em workspaces isolados (self-clean).
"""

import os
import sys
from pathlib import Path

api_path = Path(__file__).resolve().parent.parent
worker_path = api_path.parent / "worker"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

from bioma_api.db import connect  # noqa: E402
from bioma_api.repositories import brand_book as brand_repo  # noqa: E402
from bioma_api.repositories import editorial_calendar as cal_repo  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace  # noqa: E402

SERVICE_TOKEN = "smoke-mcp-token"


def main() -> None:
    print("Testing Brand Book Versionado, Editorial Calendar & Bioma MCP Server...")

    workspace = create_smoke_workspace("McpBrandCalendar")
    other_client = create_smoke_workspace("McpOtherClient")

    # Configura o processo ANTES de importar mcp_server: os módulos lêem
    # MCP_SERVICE_TOKEN/MCP_WORKSPACE_ID uma única vez, no import.
    os.environ["MCP_SERVICE_TOKEN"] = SERVICE_TOKEN
    os.environ["MCP_WORKSPACE_ID"] = str(workspace.workspace_id)
    from bioma_api import mcp_server  # noqa: E402

    try:
        with connect() as conn:
            book = brand_repo.upsert_brand_book(
                conn,
                workspace.workspace_id,
                {
                    "tom_de_voz": "Audacioso, Estratégico e Inovador",
                    "arquetipo": "O Criador / O Especialista",
                    "posicionamento": "Líder em Inteligência Artificial Operacional",
                    "proposta_valor": "Multiplique sua agência sem multiplicar equipe.",
                    "regras_copy": ["Usar dados concretos", "Evitar jargões vazios"],
                    "paleta_cores": ["#10B981", "#0F172A", "#F8FAFC"],
                },
            )
            assert book["version"] >= 1
            assert book["tom_de_voz"] == "Audacioso, Estratégico e Inovador"
            print(f"[OK] Brand Book Versionado v{book['version']} Upserted in Postgres OK")

            item = cal_repo.create_calendar_item(
                conn,
                workspace.workspace_id,
                {
                    "title": "Post Lançamento Novo Módulo de IA Bioma",
                    "content_type": "social_post",
                    "channel": "instagram",
                    "stage": "ideation",
                    "post_text": "O futuro da gestão com IA chegou...",
                    "media_urls": ["https://assets.evergreen.com/art_01.png"],
                },
            )
            assert item["stage"] == "ideation"
            updated_item = cal_repo.update_calendar_stage(conn, workspace.workspace_id, item["id"], "approved")
            assert updated_item["stage"] == "approved"
            print("[OK] Editorial Calendar Item Created & Promoted to Approved OK")

        ws_str = str(workspace.workspace_id)

        # Sem service_token: recusado, mesmo pedindo um workspace válido.
        try:
            mcp_server.handle_tool_call("bioma_get_brand_book", {"workspace_id": ws_str})
            raise AssertionError("deveria ter recusado chamada sem service_token")
        except mcp_server.McpAuthError:
            pass
        print("[OK] MCP recusa chamada sem service_token")

        # Token certo, mas workspace de outro cliente: recusado (nunca cross-workspace).
        try:
            mcp_server.handle_tool_call(
                "bioma_get_brand_book",
                {"service_token": SERVICE_TOKEN, "workspace_id": str(other_client.workspace_id)},
            )
            raise AssertionError("deveria ter recusado workspace de outro cliente")
        except mcp_server.McpAuthError:
            pass
        print("[OK] MCP recusa workspace diferente do configurado")

        # Token certo + workspace exatamente o configurado: sucesso.
        mcp_brand = mcp_server.handle_tool_call("bioma_get_brand_book", {"service_token": SERVICE_TOKEN, "workspace_id": ws_str})
        assert mcp_brand["tom_de_voz"] == "Audacioso, Estratégico e Inovador"
        print("[OK] MCP Tool 'bioma_get_brand_book' JSON-RPC Handler OK")

        mcp_raio_x = mcp_server.handle_tool_call("bioma_get_raio_x", {"service_token": SERVICE_TOKEN, "workspace_id": ws_str})
        assert "scores" in mcp_raio_x
        print("[OK] MCP Tool 'bioma_get_raio_x' JSON-RPC Handler OK")

        mcp_finops = mcp_server.handle_tool_call("bioma_get_finops", {"service_token": SERVICE_TOKEN, "workspace_id": ws_str})
        assert "total_tokens" in mcp_finops
        print("[OK] MCP Tool 'bioma_get_finops' JSON-RPC Handler OK")

        mcp_squad = mcp_server.handle_tool_call(
            "bioma_run_squad",
            {"service_token": SERVICE_TOKEN, "workspace_id": ws_str, "pilar": "oferta", "squad_name": "Squad MCP smoke"},
        )
        assert "execution_id" in mcp_squad
        print("[OK] MCP Tool 'bioma_run_squad' JSON-RPC Handler OK")

        print("\nBIOMA MCP SERVER, BRAND BOOK & EDITORIAL CALENDAR SMOKE TEST OK!")
    finally:
        cleanup_smoke_data([workspace.organization_id, other_client.organization_id], [])
        os.environ.pop("MCP_SERVICE_TOKEN", None)
        os.environ.pop("MCP_WORKSPACE_ID", None)


if __name__ == "__main__":
    main()
