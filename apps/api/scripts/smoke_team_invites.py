"""Smoke do convite ao time da EG, contra o Postgres real.

Por que existe: até 2026-08-07 não havia como convidar alguém da EG. `invites`
travava `role` em `client_user` e o serviço recusava workspace interno
(`require_kind="client"`), então colocar uma pessoa no time exigia que ela JÁ
tivesse conta. A tela dizia "Funcionalidade em breve" e estava certa.

O convite de time reusa o fluxo público de aceite (token com hash, expiração,
uso único, criação de conta e sessão) e muda só o que o aceite CONCEDE. É
exatamente esse "só" que este smoke fixa.

Valida:
- convite de time cria a pessoa como membro da organização da EG (`eg_admin`),
  não como `client_user`;
- a pessoa já entra NA EQUIPE e com o papel de tenant pedidos — sem segundo
  passo manual, que é onde se esquece;
- convite de cliente continua criando `client_user` e sem equipe (regressão);
- e-mail que já tem conta é recusado com 409, em vez de criar duplicata;
- equipe de outra organização é recusada (422);
- convidar é EG-only.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uuid import uuid4

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"
INVITED_EMAIL = "smoke-team-invite-novo@bioma.example.com"
EXISTING_EMAIL = "smoke-team-invite-existente@bioma.example.com"
OUTSIDER_EMAIL = "smoke-team-invite-cliente@bioma.example.com"
ADMIN_INVITE_EMAIL = "smoke-team-invite-socio@bioma.example.com"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    workspace = create_smoke_workspace("TEAMINVITE")
    outsider_id = upsert_smoke_user(OUTSIDER_EMAIL, "Smoke Cliente", PASSWORD)
    grant_client_user(workspace, outsider_id)
    upsert_smoke_user(EXISTING_EMAIL, "Smoke Já Existe", PASSWORD)

    team_id = None
    atexit.register(cleanup_smoke_data, [workspace.organization_id], [OUTSIDER_EMAIL, EXISTING_EMAIL, INVITED_EMAIL, ADMIN_INVITE_EMAIL])

    try:
        with connect() as conn:
            eg = conn.execute("select id from organizations where slug = 'eg'").fetchone()
            if not eg:
                raise AssertionError("Organização EG não encontrada — rode o seed.")
            eg_id = eg["id"]
            team_id = conn.execute(
                "insert into teams (tenant_organization_id, name, slug) values (%s, %s, %s) returning id",
                (eg_id, f"Smoke Convite {uuid4().hex[:6]}", f"smoke-convite-{uuid4().hex[:8]}"),
            ).fetchone()["id"]

        admin = TestClient(app)
        assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")

        # ---------------------------------------------------------------- 1
        response = admin.post(
            f"/tenants/{eg_id}/invites",
            json={"email": INVITED_EMAIL, "team_id": str(team_id), "tenant_role": "operator"},  # sem `role`: default
        )
        assert_status(response, 201, "criar convite de time")
        token = response.json()["token"]
        print("ok: convite de time criado")

        # A tela pública precisa dizer para QUAL equipe a pessoa foi chamada.
        public = admin.get(f"/auth/invites/{token}")
        assert_status(public, 200, "convite de time visível publicamente")
        if not public.json().get("team_name"):
            raise AssertionError(f"convite não informou a equipe: {public.json()}")
        print(f"ok: tela pública nomeia a equipe ({public.json()['team_name']})")

        # ---------------------------------------------------------------- 2
        convidado = TestClient(app)
        response = convidado.post(
            f"/auth/invites/{token}/accept",
            json={"display_name": "Smoke Convidado", "email": INVITED_EMAIL, "password": PASSWORD},
        )
        assert_status(response, 200, "aceitar convite de time")

        with connect() as conn:
            new_user = conn.execute("select id from users where lower(email) = %s", (INVITED_EMAIL,)).fetchone()
            if not new_user:
                raise AssertionError("usuário não foi criado")
            membership = conn.execute(
                "select role from memberships where user_id = %s and organization_id = %s",
                (new_user["id"], eg_id),
            ).fetchone()
            # Default é `eg_member` (0090). Se isto voltar a ser `eg_admin`,
            # convidar estagiário volta a criar administrador — que foi o bug.
            if not membership or membership["role"] != "eg_member":
                raise AssertionError(f"convite sem papel explícito deveria criar eg_member: {membership}")
            in_team = conn.execute(
                "select 1 from team_memberships where team_id = %s and user_id = %s",
                (team_id, new_user["id"]),
            ).fetchone()
            if not in_team:
                raise AssertionError("a pessoa não entrou na equipe pedida")
            tenant = conn.execute(
                "select role from tenant_memberships where tenant_organization_id = %s and user_id = %s",
                (eg_id, new_user["id"]),
            ).fetchone()
            if not tenant or tenant["role"] != "operator":
                raise AssertionError(f"papel de tenant não aplicado: {tenant}")
        print("ok: convidado entrou como eg_member (default), na equipe e com papel de tenant")

        # Admin continua possível — mas só quando pedido.
        response = admin.post(
            f"/tenants/{eg_id}/invites",
            json={"email": ADMIN_INVITE_EMAIL, "role": "eg_admin"},
        )
        assert_status(response, 201, "convite explicito de admin")
        admin_token = response.json()["token"]
        assert_status(
            TestClient(app).post(
                f"/auth/invites/{admin_token}/accept",
                json={"display_name": "Smoke Socio", "email": ADMIN_INVITE_EMAIL, "password": PASSWORD},
            ),
            200,
            "aceitar convite de admin",
        )
        with connect() as conn:
            socio = conn.execute("select id from users where lower(email) = %s", (ADMIN_INVITE_EMAIL,)).fetchone()
            role = conn.execute(
                "select role from memberships where user_id = %s and organization_id = %s",
                (socio["id"], eg_id),
            ).fetchone()
        if not role or role["role"] != "eg_admin":
            raise AssertionError(f"convite explicito de admin nao criou admin: {role}")
        print("ok: administrador continua possivel, mas so quando pedido")

        # ---------------------------------------------------------------- 3
        # Convite não é reutilizável.
        reuse = TestClient(app).post(
            f"/auth/invites/{token}/accept",
            json={"display_name": "Outro", "email": "smoke-team-invite-outro@bioma.example.com", "password": PASSWORD},
        )
        if reuse.status_code != 404:
            raise AssertionError(f"convite de time foi reutilizado: {reuse.status_code}")
        print("ok: convite é de uso único")

        # ---------------------------------------------------------------- 4
        assert_status(
            admin.post(f"/tenants/{eg_id}/invites", json={"email": EXISTING_EMAIL}),
            409,
            "convidar quem já tem conta",
        )
        print("ok: e-mail com conta existente é recusado (409), sem duplicar usuário")

        # ---------------------------------------------------------------- 5
        # Equipe de outra organização não cola num convite da EG.
        with connect() as conn:
            other_team = conn.execute(
                "insert into teams (tenant_organization_id, name, slug) values (%s, %s, %s) returning id",
                (workspace.organization_id, "Smoke Equipe Fora", f"smoke-fora-{uuid4().hex[:8]}"),
            ).fetchone()["id"]
        assert_status(
            admin.post(f"/tenants/{eg_id}/invites", json={"email": None, "team_id": str(other_team)}),
            422,
            "equipe de outra organização",
        )
        print("ok: equipe de outra organização é recusada (422)")

        # Guarda-corpo de dominio: so vale quando configurado, e a mensagem diz
        # quais dominios sao aceitos.
        import bioma_api.config as config_module
        original = config_module.get_settings
        try:
            base = original()
            config_module.get_settings = lambda: base.model_copy(
                update={"eg_invite_allowed_domains": "evergreenmkt.com.br"}
            )
            import bioma_api.services.invites as invites_module
            invites_module.get_settings = config_module.get_settings
            response = admin.post(
                f"/tenants/{eg_id}/invites",
                json={"email": "estranho@gmail.com"},
            )
            if response.status_code != 422 or "evergreenmkt.com.br" not in response.text:
                raise AssertionError(f"dominio fora da lista deveria ser recusado com a lista: {response.text}")
            print("ok: dominio fora da lista e recusado, e a mensagem diz quais valem")
        finally:
            config_module.get_settings = original
            invites_module.get_settings = original

        # ---------------------------------------------------------------- 6
        cliente = TestClient(app)
        assert_status(cliente.post("/auth/login", json={"email": OUTSIDER_EMAIL, "password": PASSWORD}), 200, "login cliente")
        assert_status(cliente.post(f"/tenants/{eg_id}/invites", json={"email": None}), 403, "cliente convidando")
        print("ok: convidar para o time é EG-only")

        # ---------------------------------------------------------------- 7
        # Regressão: convite de cliente continua sendo client_user, sem equipe.
        response = admin.post(f"/clients/{workspace.client_id}/invites", json={})
        assert_status(response, 201, "convite de cliente")
        client_invite = admin.get(f"/clients/{workspace.client_id}/invites").json()
        if any(item.get("team_id") for item in client_invite):
            raise AssertionError("convite de cliente saiu com equipe da EG")
        print("ok: convite de cliente segue sem equipe (regressão)")

        print("\nSMOKE TEAM INVITES: OK")
    finally:
        with connect() as conn:
            conn.execute("delete from teams where name like 'Smoke Convite %' or name = 'Smoke Equipe Fora'")
            if team_id:
                conn.execute("delete from teams where id = %s", (team_id,))
        cleanup_smoke_data(
            [workspace.organization_id], [OUTSIDER_EMAIL, EXISTING_EMAIL, INVITED_EMAIL, ADMIN_INVITE_EMAIL]
        )


if __name__ == "__main__":
    main()
