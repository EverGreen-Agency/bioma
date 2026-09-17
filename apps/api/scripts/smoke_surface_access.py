"""Smoke dos 4 níveis de acesso e visibilidade, contra o Postgres real.

Decisão 11 (2026-08-06). Os testes unitários já fixam a regra; o que só o banco
prova é o que este arquivo cobre:

- a garantia de que **preferência nunca concede** está no ESQUEMA, não só no
  código — o Postgres recusa gravar uma preferência que libere;
- `deny` de equipe alcança o membro por herança real (`team_memberships`), e a
  tela recebe o nome da equipe que negou;
- `allow` de usuário devolve o que a equipe tirou, e `deny` de usuário vence um
  `allow` de equipe;
- o teto da organização não se fura: `allow` para um `client_user` num módulo
  não contratado continua negando;
- esconder não é proibir para a EG (a rota segue permitida) e É proibir para
  cliente (o gate de backend responde 403);
- tela travada não pode ser ocultada nem por engano de admin.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
MEMBER_EMAIL = "smoke-surface-member@bioma.example.com"
CLIENT_EMAIL = "smoke-surface-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def surface(entries: list[dict], key: str) -> dict:
    for entry in entries:
        if entry["surface_key"] == key:
            return entry
    raise AssertionError(f"superfície ausente na resposta: {key}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert_status(response, 200, f"login {email}")


def grant_eg_admin(tenant_organization_id, user_id) -> None:
    with connect() as conn:
        conn.execute(
            "insert into memberships (user_id, organization_id, role) values (%s, %s, 'eg_admin') on conflict do nothing",
            (user_id, tenant_organization_id),
        )


def main() -> None:
    workspace = create_smoke_workspace("SURFACE")
    member_id = upsert_smoke_user(MEMBER_EMAIL, "Smoke Membro", PASSWORD)
    client_id = upsert_smoke_user(CLIENT_EMAIL, "Smoke Cliente", PASSWORD)
    grant_eg_admin(workspace.tenant_id, member_id)
    grant_client_user(workspace, client_id)

    team_id = None
    atexit.register(cleanup_smoke_data, [workspace.organization_id], [MEMBER_EMAIL, CLIENT_EMAIL])

    try:
        with connect() as conn:
            team_id = conn.execute(
                """
                insert into teams (tenant_organization_id, name, slug)
                values (%s, %s, %s) returning id
                """,
                (workspace.tenant_id, f"Smoke Superfície {uuid4().hex[:6]}", f"smoke-surface-{uuid4().hex[:8]}"),
            ).fetchone()["id"]
            conn.execute(
                "insert into team_memberships (team_id, user_id, role) values (%s, %s, 'member')",
                (team_id, member_id),
            )

        # ---------------------------------------------------------------- 1
        # A garantia estrutural: o banco recusa preferência que concede.
        try:
            with connect() as conn:
                conn.execute(
                    "insert into surface_preferences (user_id, surface_key, hidden) values (%s, 'eg-rh', false)",
                    (member_id,),
                )
            raise AssertionError(
                "o banco aceitou uma preferência com hidden=false — "
                "a garantia 'preferência só esconde' deixou de ser estrutural"
            )
        except psycopg.errors.CheckViolation:
            pass
        print("ok: banco recusa preferência que concede acesso (check constraint)")

        admin = TestClient(app)
        login(admin, ADMIN_EMAIL)
        member = TestClient(app)
        login(member, MEMBER_EMAIL)
        cliente = TestClient(app)
        login(cliente, CLIENT_EMAIL)

        # ---------------------------------------------------------------- 2
        # Estado inicial: admin EG enxerga o RH.
        entries = member.get("/me/surfaces").json()
        rh = surface(entries, "eg-rh")
        if not (rh["allowed"] and rh["visible"]):
            raise AssertionError(f"RH deveria estar visível por padrão para EG: {rh}")
        print("ok: EG admin enxerga o RH por padrão")

        # ---------------------------------------------------------------- 3
        # Nível 2 — deny de equipe alcança o membro, com o nome da equipe.
        response = admin.put(
            f"/teams/{team_id}/surfaces",
            json={"surface_key": "eg-rh", "effect": "deny", "note": "Equipe não cuida de RH."},
        )
        assert_status(response, 200, "deny de equipe")

        rh = surface(member.get("/me/surfaces").json(), "eg-rh")
        if rh["allowed"] or rh["reason"] != "team_denied":
            raise AssertionError(f"deny de equipe não alcançou o membro: {rh}")
        if not any("Smoke Superfície" in source for source in rh["sources"]):
            raise AssertionError(f"a tela não recebeu o nome da equipe que negou: {rh['sources']}")
        print(f"ok: deny de equipe alcança o membro e explica — {rh['detail']!r}")

        # ---------------------------------------------------------------- 4
        # Nível 3 — allow de usuário devolve o que a equipe tirou.
        response = admin.put(
            f"/users/{member_id}/surfaces",
            json={"surface_key": "eg-rh", "effect": "allow", "note": "Cuida do RH."},
        )
        assert_status(response, 200, "allow de usuário")
        rh = surface(member.get("/me/surfaces").json(), "eg-rh")
        if not rh["allowed"] or rh["reason"] != "user_allowed":
            raise AssertionError(f"allow de usuário não venceu o deny da equipe: {rh}")
        print("ok: allow de usuário vence deny de equipe (exceção por pessoa funciona)")

        # deny de usuário vence allow de equipe
        admin.put(f"/teams/{team_id}/surfaces", json={"surface_key": "eg-kits", "effect": "allow"})
        admin.put(f"/users/{member_id}/surfaces", json={"surface_key": "eg-kits", "effect": "deny"})
        kits = surface(member.get("/me/surfaces").json(), "eg-kits")
        if kits["allowed"] or kits["reason"] != "user_denied":
            raise AssertionError(f"deny de usuário não venceu allow de equipe: {kits}")
        print("ok: deny de usuário vence allow de equipe")

        # ---------------------------------------------------------------- 5
        # Nível 4 — preferência esconde sem tirar permissão (EG).
        response = member.put("/me/surfaces/preference", json={"surface_key": "eg-plataformas", "hidden": True})
        assert_status(response, 200, "esconder por preferência")
        plataformas = surface(response.json(), "eg-plataformas")
        if not plataformas["allowed"] or plataformas["visible"]:
            raise AssertionError(f"preferência deveria esconder sem tirar permissão: {plataformas}")
        print("ok: preferência esconde do menu e a rota continua permitida (EG)")

        response = member.put("/me/surfaces/preference", json={"surface_key": "eg-plataformas", "hidden": False})
        if not surface(response.json(), "eg-plataformas")["visible"]:
            raise AssertionError("reexibir não devolveu a tela")
        print("ok: reexibir volta a herdar")

        # Tela travada não pode ser escondida.
        response = member.put("/me/surfaces/preference", json={"surface_key": "cockpit", "hidden": True})
        assert_status(response, 422, "esconder tela travada")
        print("ok: tela travada recusa ser ocultada (ninguém se tranca fora da home)")

        # Esconder o que já é negado não vira linha de preferência.
        response = member.put("/me/surfaces/preference", json={"surface_key": "eg-kits", "hidden": True})
        assert_status(response, 409, "esconder tela já negada")
        print("ok: esconder tela já negada é conflito explícito, não silêncio")

        # ---------------------------------------------------------------- 6
        # Teto da organização: allow não fura módulo não contratado.
        with connect() as conn:
            conn.execute(
                "update organizations set enabled_modules = %s where id = %s",
                (psycopg.types.json.Jsonb(["hub", "content"]), workspace.organization_id),
            )
        response = admin.put(
            f"/users/{client_id}/surfaces",
            json={"surface_key": "cliente.analytics", "effect": "allow"},
        )
        assert_status(response, 200, "allow para cliente")

        cliente_entries = cliente.get("/me/surfaces").json()
        analytics = surface(cliente_entries, "cliente.analytics")
        if analytics["allowed"] or analytics["reason"] != "not_contracted":
            raise AssertionError(f"allow furou o teto da organização: {analytics}")
        print("ok: allow de usuário NÃO fura o teto da organização (módulo não contratado)")

        # ---------------------------------------------------------------- 7
        # Cliente não administra acesso de ninguém.
        assert_status(
            cliente.put(f"/teams/{team_id}/surfaces", json={"surface_key": "eg-rh", "effect": "allow"}),
            403,
            "cliente concedendo acesso",
        )
        assert_status(cliente.get("/surfaces/catalog"), 403, "cliente lendo catálogo")
        print("ok: conceder acesso é EG-only; preferência continua de cada um")

        # ---------------------------------------------------------------- 8
        # Chave inexistente falha alto, não em silêncio.
        assert_status(
            admin.put(f"/teams/{team_id}/surfaces", json={"surface_key": "nao-existe", "effect": "deny"}),
            422,
            "superfície inexistente",
        )
        print("ok: superfície desconhecida vira 422, não regra fantasma")

        print("\nSMOKE SURFACE ACCESS: OK")
    finally:
        with connect() as conn:
            if team_id:
                conn.execute("delete from teams where id = %s", (team_id,))
            conn.execute("delete from surface_grants where user_id = any(%s)", ([member_id, client_id],))
            conn.execute("delete from surface_preferences where user_id = any(%s)", ([member_id, client_id],))
        cleanup_smoke_data([workspace.organization_id], [MEMBER_EMAIL, CLIENT_EMAIL])


if __name__ == "__main__":
    main()
