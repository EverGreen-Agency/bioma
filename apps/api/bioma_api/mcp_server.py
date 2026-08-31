"""Servidor MCP stdio para orquestração externa (Fóton/Antigravity).

Como é um subprocesso stdio (sem sessão HTTP/login), a autorização usa um
segredo compartilhado (MCP_SERVICE_TOKEN) exigido em toda chamada, mais um
workspace fixo por instância (MCP_WORKSPACE_ID): todo workspace_id recebido
precisa ser exatamente esse, ou a chamada é recusada. Não usamos tenant como
escopo porque hoje só existe um tenant (a própria EG) — todos os clientes são
workspaces filhos dele, então "isolar por tenant" não isolaria cliente nenhum
de outro. Isolar por workspace é o que de fato impede uma instância de
alcançar os dados de um cliente diferente do que ela foi configurada para
atender. Falha fechado: sem os dois configurados, o processo recusa iniciar.
"""

import hmac
import json
import os
import sys
from uuid import UUID
from typing import Any

from bioma_api.db import connect
from bioma_api.repositories import brand_book as brand_repo
from bioma_api.repositories import commercial as commercial_repo
from bioma_api.repositories import squads as squads_repo
from bioma_api.repositories import whatsapp as wa_repo
from bioma_api.crypto import decrypt_secret
from bioma_api.worker_bridge import execute_squad_pipeline_safe, get_whatsapp_provider_safe


SERVICE_TOKEN = os.environ.get("MCP_SERVICE_TOKEN")
WORKSPACE_ID = os.environ.get("MCP_WORKSPACE_ID")


class McpAuthError(Exception):
    pass


MCP_TOOLS = [
    {
        "name": "bioma_get_raio_x",
        "description": "Consulta a nota dos 3 pilares comercial (Oferta, Demanda, Conversão), réguas ativas, gargalo prioritário e sprints de 90 dias.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_token": {"type": "string", "description": "Segredo compartilhado do serviço MCP"},
                "workspace_id": {"type": "string", "description": "UUID do Workspace no Bioma"},
            },
            "required": ["service_token", "workspace_id"],
        },
    },
    {
        "name": "bioma_run_squad",
        "description": "Executa a esteira de Agentes Autônomos por pilar (oferta, demanda ou conversao) e contabiliza FinOps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_token": {"type": "string"},
                "workspace_id": {"type": "string"},
                "pilar": {"type": "string", "enum": ["oferta", "demanda", "conversao"]},
                "squad_name": {"type": "string"},
            },
            "required": ["service_token", "workspace_id", "pilar", "squad_name"],
        },
    },
    {
        "name": "bioma_send_whatsapp",
        "description": "Envia mensagem de texto ou template via provedor ativo de WhatsApp (Evolution API, Meta Cloud Oficial ou Z-API).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_token": {"type": "string"},
                "workspace_id": {"type": "string"},
                "provider_type": {"type": "string", "enum": ["evolution", "meta_cloud", "zapi", "custom"]},
                "to_number": {"type": "string"},
                "message_text": {"type": "string"},
            },
            "required": ["service_token", "workspace_id", "provider_type", "to_number", "message_text"],
        },
    },
    {
        "name": "bioma_get_finops",
        "description": "Consulta o consumo total de tokens IA (prompt + completion) e o custo estimado em R$ por workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_token": {"type": "string"},
                "workspace_id": {"type": "string"},
            },
            "required": ["service_token", "workspace_id"],
        },
    },
    {
        "name": "bioma_get_brand_book",
        "description": "Consulta o Tom de Voz, Arquétipo, Posicionamento e Regras de Copy ativas do workspace no Bioma.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_token": {"type": "string"},
                "workspace_id": {"type": "string"},
            },
            "required": ["service_token", "workspace_id"],
        },
    },
]


def _require_authorized_workspace(conn, arguments: dict[str, Any]) -> UUID:
    token = arguments.get("service_token")
    if not token or not SERVICE_TOKEN or not hmac.compare_digest(token, SERVICE_TOKEN):
        raise McpAuthError("service_token ausente ou inválido.")

    requested = arguments.get("workspace_id")
    if not requested or requested != WORKSPACE_ID:
        # Mesma mensagem para "não existe" e "workspace diferente do configurado":
        # nunca confirmar a existência de um workspace fora do escopo autorizado.
        raise McpAuthError("Workspace fora do escopo autorizado para este serviço MCP.")

    ws_id = UUID(requested)
    row = conn.execute("select 1 from workspaces where id = %s and status = 'active'", (ws_id,)).fetchone()
    if not row:
        raise McpAuthError("Workspace fora do escopo autorizado para este serviço MCP.")
    return ws_id


def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    with connect() as conn:
        ws_id = _require_authorized_workspace(conn, arguments)

        if name == "bioma_get_raio_x":
            scores = commercial_repo.get_commercial_scores(conn, ws_id)
            plans = commercial_repo.list_action_plans(conn, ws_id)
            return {"scores": dict(scores), "action_plans": [dict(p) for p in plans]}

        elif name == "bioma_run_squad":
            pilar = arguments["pilar"]
            squad_name = arguments["squad_name"]
            res = execute_squad_pipeline_safe(pilar=pilar, squad_name=squad_name, input_data={})
            log = squads_repo.create_execution(
                conn,
                ws_id,
                {
                    "pilar": pilar,
                    "squad_name": squad_name,
                    "triggered_by": "MCP_FOTON_SYSTEM",
                    "status": "completed",
                    "output_data": res["output_data"],
                    "token_usage": res["token_usage"],
                    "estimated_cost_cents": res["estimated_cost_cents"],
                    "execution_logs": res["execution_logs"],
                    "completed_at": res["completed_at"],
                },
            )
            return {"execution_id": str(log["id"]), "result": res["output_data"], "tokens": res["token_usage"]}

        elif name == "bioma_send_whatsapp":
            p_type = arguments["provider_type"]
            to_num = arguments["to_number"]
            msg = arguments["message_text"]
            cfg = wa_repo.get_provider_config(conn, ws_id, p_type)
            cfg_dict = dict(cfg) if cfg else {"provider_type": p_type}
            if cfg_dict.get("api_token"):
                cfg_dict["api_token"] = decrypt_secret(cfg_dict["api_token"])
            provider = get_whatsapp_provider_safe(p_type, cfg_dict)
            sent = provider.send_text_message(to_num, msg)
            log = wa_repo.log_message(
                conn,
                ws_id,
                {
                    "provider_type": p_type,
                    "to_number": to_num,
                    "message_type": "text",
                    "payload": sent,
                    "status": "sent" if sent.get("status") in ["sent", "simulated"] else "failed",
                },
            )
            return {"log_id": str(log["id"]), "status": sent.get("status")}

        elif name == "bioma_get_finops":
            return squads_repo.get_finops_summary(conn, ws_id)

        elif name == "bioma_get_brand_book":
            book = brand_repo.get_active_brand_book(conn, ws_id)
            return dict(book)

        else:
            raise ValueError(f"Ferramenta MCP '{name}' não reconhecida.")


def run_stdio_mcp_server():
    """Servidor stdio JSON-RPC 2.0 compátivel com Fóton e Antigravity."""
    if not SERVICE_TOKEN or not WORKSPACE_ID:
        print(
            "ERRO: MCP_SERVICE_TOKEN e MCP_WORKSPACE_ID são obrigatórios para iniciar o servidor MCP.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("Bioma MCP Server Iniciado (stdio)...", file=sys.stderr)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")

            if method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                try:
                    result_data = handle_tool_call(tool_name, tool_args)
                except McpAuthError as auth_err:
                    resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32001, "message": str(auth_err)}}
                    print(json.dumps(resp), flush=True)
                    continue
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result_data, ensure_ascii=False)}]},
                }
            else:
                resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

            print(json.dumps(resp), flush=True)
        except Exception as err:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(err)}}
            print(json.dumps(err_resp), flush=True)


if __name__ == "__main__":
    run_stdio_mcp_server()
