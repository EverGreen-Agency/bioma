"""Smoke do MCP remoto (HTTP) que conecta o Bioma ao ChatGPT Web.

O que este smoke existe para impedir: o servidor MCP é uma SEGUNDA porta de
entrada para os mesmos dados. Se ele tivesse política de acesso própria, um
cliente conseguiria enxergar tarefa de outro cliente pelo ChatGPT mesmo com a
tela do Bioma correta. Por isso as asserções centrais aqui são de ISOLAMENTO,
não de "a ferramenta respondeu".

Valida:
- sem token não passa (401), e o token pessoal (PAT) autentica;
- handshake do protocolo (initialize / tools/list);
- `search` e `fetch` existem com o nome exato que a OpenAI exige;
- `search` de um usuário NÃO devolve tarefa de workspace que ele não acessa;
- `fetch` de tarefa alheia é recusado mesmo com o id correto em mãos;
- criar tarefa funciona e aparece na listagem;
- falha honesta: sem permissão, a ferramenta devolve `isError` com o motivo
  real — nunca sucesso silencioso nem erro genérico.
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
CLIENT_EMAIL = "smoke-mcp-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def rpc(client: TestClient, token: str | None, method: str, params: dict | None = None, request_id: int = 1):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    body = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        body["params"] = params
    return client.post("/mcp", json=body, headers=headers)


def call_tool(client: TestClient, token: str, name: str, arguments: dict) -> dict:
    response = rpc(client, token, "tools/call", {"name": name, "arguments": arguments})
    assert_status(response, 200, f"tools/call {name}")
    return response.json()["result"]


def issue_token(session: TestClient, name: str) -> str:
    created = session.post("/auth/personal-access-tokens", json={"name": name})
    assert_status(created, 201, "criar token pessoal")
    return created.json()["token"]


def main() -> None:
    workspace = create_smoke_workspace("MCP")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "MCP Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    workspace_id = str(workspace.workspace_id)

    admin_session = TestClient(app)
    client_session = TestClient(app)
    assert_status(admin_session.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_session.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    admin_token = issue_token(admin_session, "smoke-mcp-admin")
    client_token = issue_token(client_session, "smoke-mcp-client")

    anonymous = TestClient(app)
    created_task_ids: list[str] = []
    try:
        # 1) Sem token não entra. É a porta pública do conector: se isto passar,
        # qualquer um na internet lê o Bioma.
        assert_status(rpc(anonymous, None, "tools/list"), 401, "sem token")
        assert_status(rpc(anonymous, "bioma_pat_invalido", "tools/list"), 401, "token inválido")
        print("sem token / token inválido: 401 OK")

        # 2) Handshake e catálogo.
        init = rpc(anonymous, admin_token, "initialize", {"protocolVersion": "2025-06-18"})
        assert_status(init, 200, "initialize")
        assert init.json()["result"]["serverInfo"]["name"] == "bioma", init.json()
        listed = rpc(anonymous, admin_token, "tools/list")
        assert_status(listed, 200, "tools/list")
        tool_names = {tool["name"] for tool in listed.json()["result"]["tools"]}
        # Contrato fixo da OpenAI: sem estes dois nomes exatos o ChatGPT não
        # consegue citar fonte. Renomear quebra o conector silenciosamente.
        assert {"search", "fetch"} <= tool_names, f"faltam as ferramentas obrigatórias da OpenAI: {tool_names}"
        assert "bioma_create_task" in tool_names, tool_names
        print(f"handshake ok; {len(tool_names)} ferramentas, incluindo search/fetch OK")

        # 3) Criar tarefa pelo MCP, como o ChatGPT faria.
        # Decisao 13: workspace de cliente exige projeto. O agente descobre
        # qual pela ferramenta — parametro obrigatorio e indescobrivel seria
        # ferramenta morta.
        projetos = call_tool(admin_session, admin_token, "bioma_list_projects", {
            "workspace_id": workspace_id,
        })
        project_id = projetos["structuredContent"]["projects"][0]["id"]
        print(f"listar projetos pelo MCP OK ({len(projetos['structuredContent']['projects'])})")

        created = call_tool(admin_session, admin_token, "bioma_create_task", {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "title": "Tarefa criada pelo MCP (smoke)",
            "description": "Definição de pronto do smoke.",
            "priority": "Alta",
        })
        assert created.get("isError") is not True, created
        task_id = created["structuredContent"]["id"]
        created_task_ids.append(task_id)
        print(f"criar tarefa pelo MCP OK (id {task_id[:8]})")

        # 4) A tarefa aparece na listagem do mesmo workspace.
        listing = call_tool(admin_session, admin_token, "bioma_list_tasks", {"workspace_id": workspace_id})
        titles = {item["title"] for item in listing["structuredContent"]["tasks"]}
        assert "Tarefa criada pelo MCP (smoke)" in titles, titles
        print("tarefa criada aparece em bioma_list_tasks OK")

        # 5) search encontra pelo texto e devolve o formato que a OpenAI espera.
        found = call_tool(admin_session, admin_token, "search", {"query": "criada pelo MCP"})
        results = found["structuredContent"]["results"]
        assert results, "search não encontrou a tarefa recém-criada"
        first = results[0]
        assert set(first) >= {"id", "title", "url"}, f"search precisa devolver id/title/url: {first}"
        assert first["id"].startswith("task:"), first
        print(f"search devolve {len(results)} resultado(s) no formato id/title/url OK")

        # 6) fetch abre pelo id devolvido pelo search.
        fetched = call_tool(admin_session, admin_token, "fetch", {"id": f"task:{task_id}"})
        document = fetched["structuredContent"]
        assert set(document) >= {"id", "title", "text", "url"}, document
        assert "Definição de Pronto" in document["text"], document["text"]
        print("fetch devolve o documento no formato id/title/text/url OK")

        # 7) ISOLAMENTO — o coração deste smoke. O usuário do cliente tem acesso
        # ao workspace, mas uma tarefa interna (client_visible=false) não pode
        # vazar por nenhuma das duas ferramentas de leitura.
        internal = call_tool(admin_session, admin_token, "bioma_create_task", {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "title": "Interna do MCP (nao deve vazar)",
            "client_visible": False,
        })
        internal_id = internal["structuredContent"]["id"]
        created_task_ids.append(internal_id)

        client_search = call_tool(client_session, client_token, "search", {"query": "nao deve vazar"})
        assert client_search["structuredContent"]["results"] == [], (
            f"tarefa interna vazou no search do cliente: {client_search['structuredContent']}"
        )
        client_fetch = call_tool(client_session, client_token, "fetch", {"id": f"task:{internal_id}"})
        assert client_fetch.get("isError") is True, (
            f"fetch de tarefa interna com o id em mãos tinha que ser recusado: {client_fetch}"
        )
        print("isolamento: tarefa interna não aparece no search nem no fetch do cliente OK")

        # 8) FALHA HONESTA — pedido explícito do Eduardo: "que ele consiga criar
        # as tarefas, ou saiba quando não conseguir". Cliente não tem
        # manage_work: precisa voltar isError com o motivo, não sucesso mudo.
        denied = call_tool(client_session, client_token, "bioma_create_task", {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "title": "Cliente tentando criar",
        })
        assert denied.get("isError") is True, f"cliente não pode criar tarefa: {denied}"
        message = denied["content"][0]["text"]
        assert message and "Ferramenta" not in message, f"erro precisa dizer o motivo real: {message}"
        print(f"falha honesta ao criar sem permissão: \"{message[:60]}\" OK")

        # 9) Erro de ferramenta inexistente e id malformado também são
        # resultado com motivo, não queda do protocolo.
        unknown = call_tool(admin_session, admin_token, "ferramenta_que_nao_existe", {})
        assert unknown.get("isError") is True, unknown
        bad_id = call_tool(admin_session, admin_token, "fetch", {"id": "tarefa-errada"})
        assert bad_id.get("isError") is True and "task:" in bad_id["content"][0]["text"], bad_id
        print("ferramenta inexistente e id malformado voltam com motivo, sem quebrar OK")
    finally:
        with connect() as conn:
            for task_id in created_task_ids:
                conn.execute("delete from eg_tasks where id = %s", (task_id,))
            conn.execute(
                "delete from personal_access_tokens where name in ('smoke-mcp-admin', 'smoke-mcp-client')"
            )
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_mcp_http passou")


if __name__ == "__main__":
    main()
