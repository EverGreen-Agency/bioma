#!/usr/bin/env python3
"""Bioma n8n MCP Server.

Servidor MCP (Model Context Protocol) sobre stdio para gerenciamento completo do n8n
pelo agente de inteligência artificial do Bioma (inspeção, criação, atualização e logs).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

N8N_API_URL = os.getenv("N8N_API_URL", "http://localhost:5678").rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


def n8n_request(method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
    """Executa requisição HTTP síncrona contra a API REST do n8n."""
    url = f"{N8N_API_URL}/api/v1{endpoint}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY

    payload = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 204:
                return {}
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        return {
            "error": True,
            "status_code": e.code,
            "message": f"HTTP {e.code}: {e.reason}",
            "details": err_body,
        }
    except Exception as e:
        return {
            "error": True,
            "message": str(e),
        }


# ==============================================================================
# Definição das Ferramentas MCP
# ==============================================================================
TOOLS = [
    {
        "name": "n8n_health_check",
        "description": "Verifica a conectividade e status da instância do n8n.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "n8n_list_workflows",
        "description": "Lista todos os workflows configurados no n8n (com filtro opcional por ativos).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "active_only": {
                    "type": "boolean",
                    "description": "Se verdadeiro, lista apenas fluxos ativos.",
                },
                "tags": {
                    "type": "string",
                    "description": "Filtro opcional por tag de workflow (ex: univet).",
                },
            },
        },
    },
    {
        "name": "n8n_get_workflow",
        "description": "Obtém a definição completa em JSON de um workflow por ID (nós, parâmetros, conexões).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "description": "O ID do workflow no n8n.",
                }
            },
            "required": ["workflow_id"],
        },
    },
    {
        "name": "n8n_create_workflow",
        "description": "Cria um novo workflow no n8n.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nome do workflow"},
                "nodes": {"type": "array", "description": "Lista de nós do workflow"},
                "connections": {"type": "object", "description": "Grafo de conexões entre os nós"},
                "settings": {"type": "object", "description": "Configurações adicionais"},
            },
            "required": ["name", "nodes", "connections"],
        },
    },
    {
        "name": "n8n_update_workflow",
        "description": "Atualiza um workflow existente no n8n.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "ID do workflow a atualizar"},
                "name": {"type": "string", "description": "Nome do workflow"},
                "nodes": {"type": "array", "description": "Lista de nós atualizada"},
                "connections": {"type": "object", "description": "Grafo de conexões atualizado"},
            },
            "required": ["workflow_id"],
        },
    },
    {
        "name": "n8n_activate_workflow",
        "description": "Ativa ou pausa um workflow no n8n.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "ID do workflow"},
                "active": {"type": "boolean", "description": "True para ativar, False para pausar"},
            },
            "required": ["workflow_id", "active"],
        },
    },
    {
        "name": "n8n_get_executions",
        "description": "Consulta o histórico de execuções de fluxos no n8n (para auditar erros e falhas em nós).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Filtrar por workflow específico"},
                "limit": {"type": "integer", "description": "Quantidade máxima de execuções a retornar (padrão: 10)"},
                "status": {"type": "string", "enum": ["error", "success", "running", "waiting"], "description": "Filtrar por status"},
            },
        },
    },
]


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Any:
    if name == "n8n_health_check":
        # Tentativa de listar ou testar conexão
        res = n8n_request("GET", "/workflows?limit=1")
        if isinstance(res, dict) and res.get("error"):
            return {"status": "unhealthy", "error": res}
        return {"status": "healthy", "url": N8N_API_URL, "has_api_key": bool(N8N_API_KEY)}

    elif name == "n8n_list_workflows":
        query_params = []
        if arguments.get("active_only"):
            query_params.append("active=true")
        if arguments.get("tags"):
            query_params.append(f"tags={urllib.parse.quote(arguments['tags'])}")

        query_str = f"?{'&'.join(query_params)}" if query_params else ""
        return n8n_request("GET", f"/workflows{query_str}")

    elif name == "n8n_get_workflow":
        wid = arguments["workflow_id"]
        return n8n_request("GET", f"/workflows/{wid}")

    elif name == "n8n_create_workflow":
        payload = {
            "name": arguments["name"],
            "nodes": arguments["nodes"],
            "connections": arguments["connections"],
            "settings": arguments.get("settings", {}),
        }
        return n8n_request("POST", "/workflows", payload)

    elif name == "n8n_update_workflow":
        wid = arguments["workflow_id"]
        payload: Dict[str, Any] = {}
        if "name" in arguments:
            payload["name"] = arguments["name"]
        if "nodes" in arguments:
            payload["nodes"] = arguments["nodes"]
        if "connections" in arguments:
            payload["connections"] = arguments["connections"]
        return n8n_request("PUT", f"/workflows/{wid}", payload)

    elif name == "n8n_activate_workflow":
        wid = arguments["workflow_id"]
        action = "activate" if arguments.get("active") else "deactivate"
        return n8n_request("POST", f"/workflows/{wid}/{action}")

    elif name == "n8n_get_executions":
        params = [f"limit={arguments.get('limit', 10)}"]
        if arguments.get("workflow_id"):
            params.append(f"workflowId={arguments['workflow_id']}")
        if arguments.get("status"):
            params.append(f"status={arguments['status']}")
        return n8n_request("GET", f"/executions?{'&'.join(params)}")

    return {"error": True, "message": f"Ferramenta desconhecida: {name}"}


def send_response(response_obj: Dict[str, Any]):
    serialized = json.dumps(response_obj)
    sys.stdout.write(serialized + "\n")
    sys.stdout.flush()


def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "bioma-n8n-mcp",
                        "version": "1.0.0"
                    }
                }
            })
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS
                }
            })
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                res = handle_tool_call(tool_name, tool_args)
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(res, indent=2, ensure_ascii=False)
                            }
                        ]
                    }
                })
            except Exception as e:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "isError": True,
                        "content": [
                            {"type": "text", "text": f"Erro na execução da ferramenta: {str(e)}"}
                        ]
                    }
                })
        elif method == "ping":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            })
        else:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Método não suportado: {method}"
                }
            })


if __name__ == "__main__":
    main()
