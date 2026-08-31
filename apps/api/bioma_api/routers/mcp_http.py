"""MCP remoto (HTTP) — conecta o Bioma ao ChatGPT.

Existe separado de `bioma_api/mcp_server.py` porque os dois resolvem problemas
diferentes e NÃO dá para reaproveitar um no outro: aquele é stdio (subprocesso
local, para Fóton/Antigravity, autorizado por segredo compartilhado + workspace
fixo); este é HTTP, que é o que qualquer cliente MCP remoto exige.

**Superfície: app desktop do ChatGPT**, não a Web — ver `docs/MCP-CHATGPT.md`,
que corrigiu isso em 2026-08-06 contra a documentação oficial. Este docstring
dizia "ChatGPT Web" e ficou para trás; quem lesse só o código concluiria o
contrário do que o doc diz.

Contrato conferido contra `developers.openai.com/plugins/build/mcp-server`
(2026-08-07): transporte **Streamable HTTP** em HTTPS estável no caminho
`/mcp`, que é o que este router serve. `search` e `fetch` seguem o schema
padrão — a OpenAI só os exige para o plugin valer como fonte de conhecimento
da empresa, mas implementá-los é barato e destrava esse caso.

Limite conhecido: a autenticação aqui é **Bearer com token pessoal**. Serve
para uso interno e para o app desktop. Publicar como plugin no diretório
exigiria **OAuth 2.1** (ou mTLS gerenciado pela OpenAI), que é outro trabalho —
não uma correção deste.

## Autorização

Reaproveita `current_user_from_request` — o MESMO Bearer de token pessoal
(`bioma_pat_...`) que o resto da API já aceita desde a migration 0060. E toda
ferramenta chama a **camada de serviço**, nunca o repositório.

Isso é deliberado: o ChatGPT enxerga exatamente o que o dono do token enxerga,
nem mais nem menos. Não existe regra de permissão nova aqui para revisar — se
o usuário não pode criar tarefa num workspace pela tela, também não pode pelo
ChatGPT, pelo mesmo código. Um servidor MCP que falasse direto com o banco
seria uma segunda porta de entrada com sua própria política de acesso, e é
exatamente assim que se cria um vazamento entre clientes sem perceber.

## Falha honesta

O Eduardo pediu explicitamente que ele "consiga criar as tarefas, ou saiba
quando não conseguir". Por isso erro de ferramenta volta com `isError: true` e
a mensagem real do serviço (título vazio, workspace inexistente, sem
permissão), em vez de um genérico. O ChatGPT lê isso e consegue dizer à pessoa
o que falta — que é o ponto.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.tasks import TaskCommentCreate, TaskCreate, TaskUpdate
from bioma_api.services import projects as projects_service
from bioma_api.services import tasks as tasks_service
from bioma_api.services import workspaces as workspaces_service

router = APIRouter(prefix="/mcp", tags=["mcp"])

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "bioma", "title": "Bioma — EverGreen", "version": "1.0.0"}

# Status válidos por disciplina vivem no frontend (`lib/task-frentes.ts`), mas o
# banco aceita texto livre. Repetimos os mais usados na descrição da ferramenta
# para o modelo escolher um que a tela reconheça, em vez de inventar "todo".
COMMON_STATUSES = "Brain, Backlog, Em progresso, Em revisão, Bloqueado, Concluído, Finalizado"


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "inputSchema": {"type": "object", "properties": properties, "required": required},
    }


TOOLS = [
    # `search` e `fetch` têm contrato FIXO da OpenAI (nome, formato de entrada e
    # de saída). Não renomear nem mudar os campos: é o que o ChatGPT usa para
    # citar fonte. Ver developers.openai.com/api/docs/mcp.
    _tool(
        "search",
        "Busca tarefas do Bioma por texto no título ou na descrição. Use antes de "
        "'fetch' para descobrir o id de uma tarefa.",
        {"query": {"type": "string", "description": "Texto a procurar"}},
        ["query"],
    ),
    _tool(
        "fetch",
        "Abre um item do Bioma pelo id devolvido por 'search' (formato 'task:<uuid>').",
        {"id": {"type": "string", "description": "Id no formato 'task:<uuid>'"}},
        ["id"],
    ),
    _tool(
        "bioma_list_workspaces",
        "Lista os workspaces (clientes e Operação EG) que este usuário pode ver. "
        "Use para descobrir o workspace_id antes de listar ou criar tarefa.",
        {},
        [],
    ),
    _tool(
        "bioma_list_tasks",
        "Lista as tarefas de um workspace.",
        {
            "workspace_id": {"type": "string", "description": "UUID do workspace"},
            "discipline": {
                "type": "string",
                "description": "Filtro opcional: growth ou tech",
                "enum": ["growth", "tech"],
            },
        },
        ["workspace_id"],
    ),
    _tool(
        "bioma_list_projects",
        "Lista os projetos de um workspace. Em workspace de CLIENTE a tarefa "
        "precisa de um projeto (decisao 13), entao chame isto antes de criar.",
        {"workspace_id": {"type": "string", "description": "UUID do workspace"}},
        ["workspace_id"],
    ),
    _tool(
        "bioma_create_task",
        "Cria uma tarefa no Bioma. Requer permissão de gestão no workspace — se "
        "não tiver, a chamada falha com o motivo.",
        {
            "workspace_id": {"type": "string", "description": "UUID do workspace"},
            "title": {"type": "string", "description": "Título da tarefa"},
            "description": {
                "type": "string",
                "description": "Definição de Pronto: o critério que autoriza mover para concluído.",
            },
            "status": {"type": "string", "description": f"Status. Usados na tela: {COMMON_STATUSES}"},
            "group_status": {
                "type": "string",
                "enum": ["NOT_STARTED", "ACTIVE", "DONE", "CLOSED"],
                "description": "Coluna macro do kanban. Padrão: NOT_STARTED",
            },
            "priority": {"type": "string", "enum": ["Alta", "Média", "Baixa"]},
            "discipline": {"type": "string", "enum": ["growth", "tech"]},
            "due_date": {"type": "string", "description": "Vencimento ISO 8601 (ex: 2026-09-30T18:00:00Z)"},
            "client_visible": {
                "type": "boolean",
                "description": "Falso esconde a tarefa do usuário do cliente. Padrão: true",
            },
            "project_id": {
                "type": "string",
                "description": (
                    "UUID do projeto. OBRIGATÓRIO em workspace de cliente e opcional "
                    "na Operação EG (decisão 13). Use bioma_list_projects para achar."
                ),
            },
        },
        ["workspace_id", "title"],
    ),
    _tool(
        "bioma_update_task",
        "Atualiza uma tarefa existente. Envie apenas os campos que devem mudar.",
        {
            "task_id": {"type": "string", "description": "UUID da tarefa"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "status": {"type": "string", "description": f"Usados na tela: {COMMON_STATUSES}"},
            "group_status": {"type": "string", "enum": ["NOT_STARTED", "ACTIVE", "DONE", "CLOSED"]},
            "priority": {"type": "string", "enum": ["Alta", "Média", "Baixa"]},
            "due_date": {"type": "string", "description": "Vencimento ISO 8601"},
        },
        ["task_id"],
    ),
    _tool(
        "bioma_add_task_comment",
        "Comenta numa tarefa. O comentário nasce interno; só vai ao cliente se "
        "client_visible for true.",
        {
            "task_id": {"type": "string", "description": "UUID da tarefa"},
            "body": {"type": "string", "description": "Texto do comentário"},
            "client_visible": {"type": "boolean", "description": "Padrão: false (interno)"},
        },
        ["task_id", "body"],
    ),
]


def _task_url(task: Any) -> str:
    """Link para a tarefa dentro do Bioma.

    Relativo de propósito: a API não sabe o domínio do app web (`WEB_APP_URL` é
    do ambiente da API, e em produção web e API vivem em subdomínios
    diferentes). O ChatGPT mostra o caminho e a pessoa abre no Bioma logado.
    """
    return f"/operacao/tarefas?task={task.id}"


def _task_text(task: Any) -> str:
    parts = [
        f"Tarefa: {task.title}",
        f"Status: {task.status} ({task.group_status})",
    ]
    if task.priority:
        parts.append(f"Prioridade: {task.priority}")
    if task.discipline:
        parts.append(f"Disciplina: {task.discipline}")
    if task.due_date:
        parts.append(f"Vencimento: {task.due_date.isoformat()}")
    if task.description:
        parts.append(f"Definição de Pronto: {task.description}")
    if task.subtasks:
        done = sum(1 for item in task.subtasks if item.is_completed)
        parts.append(f"Checklist: {done}/{len(task.subtasks)} concluído(s)")
    return "\n".join(parts)


def _visible_tasks(user: CurrentUserResponse) -> list[tuple[Any, Any]]:
    """`(workspace, tarefa)` de tudo que este usuário enxerga.

    Varre workspace por workspace em vez de uma query só porque é a camada de
    serviço que aplica visibilidade (inclusive esconder tarefa interna de
    usuário do cliente). Uma query direta seria mais rápida e teria que
    reimplementar essa regra — é exatamente onde um vazamento nasceria. Com a
    carteira da EG o custo é irrelevante.
    """
    pairs: list[tuple[Any, Any]] = []
    for workspace in workspaces_service.list_workspaces(user):
        for task in tasks_service.list_workspace_tasks(workspace.id, user):
            pairs.append((workspace, task))
    return pairs


def _call_tool(name: str, args: dict[str, Any], user: CurrentUserResponse) -> dict[str, Any]:
    if name == "search":
        query = (args.get("query") or "").strip().lower()
        results = []
        for workspace, task in _visible_tasks(user):
            haystack = f"{task.title} {task.description or ''}".lower()
            if query and query not in haystack:
                continue
            results.append({
                "id": f"task:{task.id}",
                "title": f"{task.title} — {workspace.name}",
                "url": _task_url(task),
            })
        return {"results": results[:50]}

    if name == "fetch":
        raw = args.get("id") or ""
        if not raw.startswith("task:"):
            raise ValueError("id precisa estar no formato 'task:<uuid>', como devolvido por 'search'.")
        task_id = UUID(raw.removeprefix("task:"))
        for workspace, task in _visible_tasks(user):
            if task.id == task_id:
                return {
                    "id": raw,
                    "title": task.title,
                    "text": _task_text(task),
                    "url": _task_url(task),
                    "metadata": {"workspace": workspace.name, "workspace_id": str(workspace.id)},
                }
        raise ValueError("Tarefa não encontrada ou fora do seu acesso.")

    if name == "bioma_list_workspaces":
        return {
            "workspaces": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "kind": item.kind,
                    "status": item.status,
                    "access_role": item.access_role,
                }
                for item in workspaces_service.list_workspaces(user)
            ]
        }

    if name == "bioma_list_tasks":
        tasks = tasks_service.list_workspace_tasks(
            UUID(args["workspace_id"]), user, discipline=args.get("discipline")
        )
        return {
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "status": task.status,
                    "group_status": task.group_status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "client_visible": task.client_visible,
                }
                for task in tasks
            ]
        }

    if name == "bioma_list_projects":
        projetos = projects_service.list_projects(UUID(args["workspace_id"]), user)
        return {
            "projects": [
                {"id": str(p.id), "name": p.name, "status": p.status, "type": p.project_type}
                for p in projetos
            ]
        }

    if name == "bioma_create_task":
        payload = TaskCreate(
            title=args["title"],
            description=args.get("description"),
            # O modelo costuma omitir status; o padrão espelha a primeira coluna
            # do kanban, que é onde a pessoa esperaria achar a tarefa nova.
            status=args.get("status") or "Backlog",
            group_status=args.get("group_status") or "NOT_STARTED",
            priority=args.get("priority"),
            discipline=args.get("discipline"),
            due_date=args.get("due_date"),
            client_visible=args.get("client_visible", True),
            project_id=args.get("project_id"),
        )
        task = tasks_service.create_workspace_task(UUID(args["workspace_id"]), payload, user)
        return {"id": str(task.id), "title": task.title, "url": _task_url(task), "status": "created"}

    if name == "bioma_update_task":
        fields = {key: args[key] for key in
                  ("title", "description", "status", "group_status", "priority", "due_date")
                  if key in args}
        if not fields:
            raise ValueError("Envie ao menos um campo para atualizar.")
        task = tasks_service.update_task(UUID(args["task_id"]), TaskUpdate(**fields), user)
        return {"id": str(task.id), "title": task.title, "url": _task_url(task), "status": "updated"}

    if name == "bioma_add_task_comment":
        comment = tasks_service.create_task_comment(
            UUID(args["task_id"]),
            TaskCommentCreate(body=args["body"], client_visible=args.get("client_visible", False)),
            user,
        )
        return {"id": str(comment.id), "status": "created"}

    raise ValueError(f"Ferramenta '{name}' não existe neste servidor.")


def _handle(message: dict[str, Any], user: CurrentUserResponse) -> dict[str, Any] | None:
    method = message.get("method")
    message_id = message.get("id")

    # Notificação (sem id) não recebe resposta — responder quebra o protocolo.
    if message_id is None and method and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": message_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            data = _call_tool(name, args, user)
        except Exception as error:  # noqa: BLE001
            # Erro de ferramenta é RESULTADO, não erro de protocolo: o modelo
            # precisa ler o motivo e explicar à pessoa o que falta, em vez de a
            # conversa morrer com "o conector falhou".
            detail = getattr(error, "detail", None) or str(error)
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {"content": [{"type": "text", "text": str(detail)}], "isError": True},
            }
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                # Os dois formatos: `structuredContent` é o que a OpenAI lê para
                # citar fonte; o texto JSON é o fallback de compatibilidade.
                "content": [{"type": "text", "text": _json_dumps(data)}],
                "structuredContent": data,
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": -32601, "message": f"Método '{method}' não suportado."},
    }


def _json_dumps(data: Any) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, default=str)


@router.post("")
async def mcp_endpoint(
    request: Request,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    """Streamable HTTP: uma requisição JSON-RPC, uma resposta."""
    message = await request.json()
    response = _handle(message, user)
    if response is None:
        return JSONResponse(status_code=202, content=None)
    return JSONResponse(content=response)


@router.get("/sse")
async def mcp_sse(user: CurrentUserResponse = Depends(current_user_from_request)):
    """Compatibilidade com clientes que ainda abrem SSE antes do POST.

    A documentação da OpenAI ainda mostra a URL do conector terminando em
    `/sse/`. Mantemos o canal aberto e anunciamos o endpoint de POST acima;
    quem já fala Streamable HTTP usa direto a raiz `/mcp`.
    """

    async def event_stream():
        yield f"event: endpoint\ndata: /mcp\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
