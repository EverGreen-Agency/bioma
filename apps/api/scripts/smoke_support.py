from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4
import sys

# Importado pelos smokes (que já ajustam o sys.path) e também executado direto
# pelo runner, para a varredura de resíduo — daí o ajuste aqui.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg.types.json import Jsonb

from bioma_api.db import connect
from bioma_api.security import hash_password


@dataclass(frozen=True)
class SmokeWorkspace:
    tenant_id: UUID
    organization_id: UUID
    client_id: UUID
    workspace_id: UUID
    name: str
    slug: str
    # Decisao 13: tarefa de CLIENTE exige projeto, e todo workspace de smoke e
    # de cliente. Um projeto padrao vem junto porque a alternativa seria cada
    # smoke criar o seu — ou, pior, a regra ser afrouxada para o teste passar.
    project_id: UUID | None = None


def create_smoke_workspace(label: str) -> SmokeWorkspace:
    suffix = uuid4().hex[:10]
    name = f"Smoke {label} {suffix}"
    slug = f"smoke-{label.lower()}-{suffix}"
    with connect() as conn:
        tenant = conn.execute(
            "select id from organizations where slug = 'eg' and type = 'eg' order by created_at limit 1"
        ).fetchone()
        if not tenant:
            raise RuntimeError("Tenant EG não encontrado; rode seed_dev.py antes dos smokes.")
        organization_id = conn.execute(
            """
            insert into organizations (name, slug, type, parent_organization_id, enabled_modules)
            values (%s, %s, 'client', %s, %s) returning id
            """,
            (
                name,
                slug,
                tenant["id"],
                Jsonb(["hub", "content", "files", "commercial", "analytics", "integrations"]),
            ),
        ).fetchone()["id"]
        client_id = conn.execute(
            """
            insert into clients (organization_id, name, status, responsible_name)
            values (%s, %s, 'active', 'Smoke') returning id
            """,
            (organization_id, name),
        ).fetchone()["id"]
        workspace_id = conn.execute(
            """
            insert into workspaces (
              tenant_organization_id, subject_organization_id, kind, name, slug, status
            ) values (%s, %s, 'client', %s, %s, 'active') returning id
            """,
            (tenant["id"], organization_id, name, slug),
        ).fetchone()["id"]
        project_id = conn.execute(
            """
            insert into projects (
              tenant_organization_id, workspace_id, organization_id, name, status
            ) values (%s, %s, %s, %s, 'active') returning id
            """,
            (tenant["id"], workspace_id, organization_id, f"Projeto {name}"),
        ).fetchone()["id"]
    return SmokeWorkspace(
        tenant["id"], organization_id, client_id, workspace_id, name, slug, project_id
    )


def upsert_smoke_user(email: str, name: str, password: str) -> UUID:
    with connect() as conn:
        row = conn.execute("select id from users where lower(email) = lower(%s)", (email,)).fetchone()
        if row:
            conn.execute(
                "update users set display_name = %s, password_hash = %s, is_active = true where id = %s",
                (name, hash_password(password), row["id"]),
            )
            return row["id"]
        return conn.execute(
            "insert into users (email, display_name, password_hash) values (%s, %s, %s) returning id",
            (email, name, hash_password(password)),
        ).fetchone()["id"]


def grant_client_user(workspace: SmokeWorkspace, user_id: UUID) -> None:
    with connect() as conn:
        conn.execute(
            """
            insert into memberships (user_id, organization_id, role)
            values (%s, %s, 'client_user') on conflict do nothing
            """,
            (user_id, workspace.organization_id),
        )


def cleanup_smoke_data(organization_ids: list[UUID], emails: list[str]) -> None:
    with connect() as conn:
        if organization_ids:
            conn.execute("delete from organizations where id = any(%s)", (organization_ids,))
        if emails:
            conn.execute("delete from users where lower(email) = any(%s)", ([email.lower() for email in emails],))


def purge_smoke_residue() -> dict[str, int]:
    """Varredura final do runner: apaga tudo que segue a convenção de nome de smoke.

    Por que existe: a limpeza de cada smoke roda no `finally`, então uma asserção
    que quebra ANTES do `try` deixa o workspace na carteira — foi assim que cinco
    clientes "Smoke COPILOT xxx" apareceram na carteira local. Cada smoke agora
    registra um `atexit`, mas isso só cobre os smokes que usam `smoke_support`;
    `smoke_invites` e `smoke_password` criam usuários `@smoke.dev` avulsos e nunca
    limparam nada (48 usuários acumulados até 2026-07-31).

    Esta função é a rede embaixo do trapézio: roda uma vez no fim do runner e
    responde por convenção de nome, não por bookkeeping de cada script. Só apaga
    o que nenhum dado real pode se chamar.
    """
    removed = {"organizations": 0, "users": 0, "local_radar_scans": 0, "wins": 0, "sessions": 0}
    with connect() as conn:
        rows = conn.execute(
            "select id from organizations where name like 'Smoke %' and type = 'client'"
        ).fetchall()
        if rows:
            conn.execute("delete from organizations where id = any(%s)", ([row["id"] for row in rows],))
            removed["organizations"] = len(rows)

        rows = conn.execute(
            "select id from users where email like %s or email like %s",
            ("%@smoke.dev", "smoke-%@bioma.example.com"),
        ).fetchall()
        if rows:
            conn.execute("delete from users where id = any(%s)", ([row["id"] for row in rows],))
            removed["users"] = len(rows)

        rows = conn.execute(
            "select id from local_radar_scans where niche = 'smoke' or city = 'smoke'"
        ).fetchall()
        if rows:
            scan_ids = [row["id"] for row in rows]
            conn.execute("delete from local_radar_prospects where scan_id = any(%s)", (scan_ids,))
            conn.execute("delete from local_radar_scans where id = any(%s)", (scan_ids,))
            removed["local_radar_scans"] = len(rows)

        # Detector automático (`win_detectors.py`) cria vitória de verdade sobre
        # qualquer cliente `active` que encontrar — inclusive o cliente de um
        # smoke, se ele ainda existir no momento em que os detectores reais
        # rodarem. Sem `workspace_id` preenchido nesse caso, apagar o workspace
        # não leva a vitória junto (foi assim que 5 delas ficaram no mural
        # durante o desenvolvimento de `smoke_wins.py`).
        n = conn.execute("delete from wins where title like 'Cliente ativo na carteira: Smoke %'").rowcount
        removed["wins"] = n

        # Cada smoke faz 2-3 logins como o admin real, e login cria sessão. Com
        # 40 smokes por rodada isso acumulava centenas de linhas que apareciam
        # na tela "dispositivos autorizados" do Eduardo como se fossem
        # navegadores dele. O TestClient se identifica como `testclient`, então
        # dá para apagar exatamente as de teste sem tocar em sessão de gente.
        n = conn.execute("delete from sessions where user_agent = 'testclient'").rowcount
        removed["sessions"] = n
    return removed


if __name__ == "__main__":
    print(purge_smoke_residue())
