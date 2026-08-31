from pathlib import Path
import atexit
import sys
from uuid import uuid4

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.config import Settings, get_settings
from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.security import hash_session_token
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-api-client@bioma.example.com"
DEV_PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEV_PASSWORD})
    assert_status(response, 200, f"login {email}")


def expire_current_session(client: TestClient) -> None:
    settings = get_settings()
    token = client.cookies.get(settings.session_cookie_name)
    if not token:
        raise AssertionError("sessão esperada no cookie para teste de expiração")
    with connect() as conn:
        conn.execute(
            "update sessions set expires_at = now() - interval '1 second' where token_hash = %s",
            (hash_session_token(token),),
        )


def main() -> None:
    staging_settings = Settings(
        app_env="staging",
        database_url="postgresql://bioma:secret@postgres.internal:5432/bioma",
        cors_origins="https://staging.bioma.example.com",
        session_cookie_secure=True,
    )
    assert staging_settings.cookie_secure is True
    assert staging_settings.cors_origin_list == ["https://staging.bioma.example.com"]
    try:
        Settings(
            app_env="production",
            database_url="postgresql://bioma:bioma@localhost:5432/bioma",
            cors_origins="http://localhost:5173",
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("configuração de produção insegura deveria ser rejeitada")

    smoke_workspace = create_smoke_workspace("API")
    smoke_client_user_id = upsert_smoke_user(CLIENT_EMAIL, "API Client Smoke", DEV_PASSWORD)
    grant_client_user(smoke_workspace, smoke_client_user_id)

    def cleanup_initial_workspace() -> None:
        cleanup_smoke_data([smoke_workspace.organization_id], [CLIENT_EMAIL])

    atexit.register(cleanup_initial_workspace)

    admin = TestClient(app)
    guest = TestClient(app)
    client_user = TestClient(app)

    cors = guest.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert_status(cors, 200, "cors preflight")
    assert cors.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

    assert_status(guest.get("/health"), 200, "health")
    assert_status(guest.get("/health/ready"), 200, "readiness")
    assert_status(guest.get("/auth/me"), 401, "missing session")
    assert_status(guest.get("/workspaces"), 401, "workspace discovery requires session")
    # O rate limit persiste em `login_attempts`, então rodar o smoke duas vezes
    # dentro da janela fazia a primeira tentativa ja vir 429. Limpar antes torna
    # o teste idempotente sem enfraquecer o que ele valida.
    with connect() as conn:
        conn.execute("delete from login_attempts")
    for _ in range(5):
        assert_status(
            guest.post("/auth/login", json={"email": "rate-limit@example.com", "password": "wrong"}),
            401,
            "failed login before rate limit",
        )
    assert_status(
        guest.post("/auth/login", json={"email": "rate-limit@example.com", "password": "wrong"}),
        429,
        "login rate limit",
    )

    login(admin, ADMIN_EMAIL)
    login(client_user, CLIENT_EMAIL)
    assert_status(admin.get("/auth/me"), 200, "active session")
    expire_current_session(admin)
    assert_status(admin.get("/auth/me"), 401, "expired session")
    login(admin, ADMIN_EMAIL)
    assert_status(admin.post("/auth/logout"), 200, "logout revokes session")
    assert_status(admin.get("/auth/me"), 401, "revoked session")
    login(admin, ADMIN_EMAIL)

    clients_response = admin.get("/clients")
    assert_status(clients_response, 200, "admin list clients")
    clients = clients_response.json()
    assert clients, "seed precisa criar ao menos um cliente"
    hm_client = next(row for row in clients if row["id"] == str(smoke_workspace.client_id))
    hm_client_id = hm_client["id"]
    hm_organization_id = hm_client["organization_id"]

    admin_workspaces_response = admin.get("/workspaces")
    assert_status(admin_workspaces_response, 200, "admin list workspaces")
    admin_workspaces = admin_workspaces_response.json()
    internal_workspace = next(row for row in admin_workspaces if row["kind"] == "agency_internal")
    assert internal_workspace["client_id"] is None, "operação EG não pode ser uma conta cliente"
    assert internal_workspace["organization_id"] == internal_workspace["tenant_organization_id"]
    assert internal_workspace["slug"] == internal_workspace["organization_slug"]
    # A Operação EG opera pelo PRÓPRIO id. Até 2026-08-07 este smoke exigia um
    # "adapter legado" — um registro em `clients` chamado "EverGreen Internal",
    # que existia só porque o resolvedor partia de `clients` e
    # `performance_connections.client_id` era NOT NULL. As duas restrições
    # caíram (0087 + resolvedor por workspace), e a agência deixou de precisar
    # fingir que é cliente de si mesma. Se o registro antigo ainda existir num
    # banco, ele é tolerado; exigir que exista é que não faz mais sentido.
    assert_status(
        admin.post(f"/clients/{internal_workspace['id']}/invites", json={}),
        404,
        "workspace interno não aceita convite de cliente",
    )
    assert_status(admin.get(f"/clients/{internal_workspace['id']}/files"), 200, "admin opera files interno")
    assert_status(admin.get(f"/clients/{internal_workspace['id']}/performance"), 200, "admin opera performance interno")
    assert_status(admin.get(f"/workspaces/{internal_workspace['id']}/leads"), 200, "admin opera CRM interno canônico")
    assert_status(admin.get(f"/workspaces/{internal_workspace['id']}/finance"), 200, "admin opera financeiro interno canônico")
    assert_status(admin.get(f"/workspaces/{internal_workspace['id']}/performance"), 200, "admin opera Performance interno canônico")
    assert_status(
        admin.get(f"/integrations/{internal_workspace['organization_id']}/kommo"),
        200,
        "admin opera Kommo interno",
    )
    hm_workspace = next(row for row in admin_workspaces if row["id"] == str(smoke_workspace.workspace_id))
    assert hm_workspace["kind"] == "client"
    assert hm_workspace["client_id"] == hm_client_id
    legacy_portal = admin.get(f"/clients/{hm_client_id}")
    canonical_portal = admin.get(f"/workspaces/{hm_workspace['id']}")
    adapter_portal = admin.get(f"/workspaces/{hm_client_id}")
    assert_status(legacy_portal, 200, "legacy client route remains compatible")
    assert_status(canonical_portal, 200, "canonical workspace portal")
    assert_status(adapter_portal, 200, "workspace route accepts legacy client adapter")
    assert canonical_portal.json()["client"]["id"] == legacy_portal.json()["client"]["id"]
    assert_status(admin.get(f"/workspaces/{hm_workspace['id']}/files"), 200, "canonical workspace files")
    assert_status(admin.get(f"/workspaces/{hm_workspace['id']}/performance"), 200, "canonical workspace performance")
    assert_status(admin.get(f"/workspaces/{hm_workspace['id']}/invites"), 200, "canonical workspace invites")
    stable_workspace = next(
        row for row in admin.get("/workspaces").json() if row["id"] == str(smoke_workspace.workspace_id)
    )
    assert stable_workspace["id"] == hm_workspace["id"], "workspace precisa ter identidade estável"

    client_clients = client_user.get("/clients")
    assert_status(client_clients, 200, "client list clients")
    assert len(client_clients.json()) == 1, "cliente deve enxergar apenas a própria organização no seed"
    client_workspaces_response = client_user.get("/workspaces")
    assert_status(client_workspaces_response, 200, "client list workspaces")
    client_workspaces = client_workspaces_response.json()
    assert len(client_workspaces) == 1, "cliente deve enxergar somente o próprio workspace"
    assert client_workspaces[0]["organization_slug"] == smoke_workspace.slug
    assert all(row["kind"] != "agency_internal" for row in client_workspaces)
    assert_status(
        client_user.get(f"/workspaces/{hm_workspace['id']}"),
        200,
        "client accesses canonical own workspace",
    )

    # Mesmo uma membership legada indevida na organização EG não pode
    # transformar a operação interna em workspace/cliente acessível.
    with connect() as conn:
        client_user_id = conn.execute(
            "select id from users where lower(email) = lower(%s)",
            (CLIENT_EMAIL,),
        ).fetchone()["id"]
        existing_internal_membership = conn.execute(
            "select role from memberships where user_id = %s and organization_id = %s",
            (client_user_id, internal_workspace["organization_id"]),
        ).fetchone()
        if not existing_internal_membership:
            conn.execute(
                "insert into memberships (user_id, organization_id, role) values (%s, %s, 'client_user')",
                (client_user_id, internal_workspace["organization_id"]),
            )
    try:
        guarded_workspaces = client_user.get("/workspaces")
        assert_status(guarded_workspaces, 200, "membership interna não vaza workspace")
        assert all(row["kind"] != "agency_internal" for row in guarded_workspaces.json())
        assert_status(
            client_user.get(f"/clients/{internal_workspace['id']}"),
            404,
            "membership interna não vaza adapter cliente",
        )
        assert_status(
            client_user.get(f"/workspaces/{internal_workspace['id']}"),
            404,
            "membership interna não vaza rota canônica",
        )
        assert_status(
            client_user.get(f"/clients/{internal_workspace['id']}/files"),
            404,
            "membership interna não vaza files",
        )
        assert_status(
            client_user.get(f"/clients/{internal_workspace['id']}/performance"),
            404,
            "membership interna não vaza performance",
        )
        assert_status(
            client_user.get(f"/integrations/{internal_workspace['organization_id']}/kommo"),
            404,
            "membership interna não vaza Kommo",
        )
    finally:
        if not existing_internal_membership:
            with connect() as conn:
                conn.execute(
                    "delete from memberships where user_id = %s and organization_id = %s",
                    (client_user_id, internal_workspace["organization_id"]),
                )

    # O adapter ClickUp foi retirado (migração 0034). As asserções de
    # /sync/clickup ficaram cobrando um endpoint inexistente e mascaravam a
    # suíte com falha permanente; o bloqueio de escrita do client_user segue
    # coberto pelos casos de deliverable/artefato abaixo.
    approval_deliverable = admin.post(
        f"/clients/{hm_client_id}/deliverables",
        json={"title": "Entrega para aprovação smoke", "status": "in_progress"},
    )
    assert_status(approval_deliverable, 201, "create deliverable for approval")
    approval_deliverable_id = next(
        item["id"]
        for item in approval_deliverable.json()["deliverables"]
        if item["title"] == "Entrega para aprovação smoke"
    )
    requested_approval = admin.post(
        f"/clients/{hm_client_id}/approvals",
        json={"deliverable_id": approval_deliverable_id, "comment": "Validar entrega smoke."},
    )
    assert_status(requested_approval, 201, "request approval")
    approval_id = next(
        item["id"]
        for item in requested_approval.json()["approvals"]
        if item["deliverable_id"] == approval_deliverable_id and item["status"] == "pending"
    )
    decided_approval = client_user.patch(
        f"/clients/{hm_client_id}/approvals/{approval_id}",
        json={"status": "approved", "comment": "Aprovado pelo smoke."},
    )
    assert_status(decided_approval, 200, "client decides approval")
    assert any(
        item["id"] == approval_deliverable_id and item["status"] == "done"
        for item in decided_approval.json()["deliverables"]
    )
    assert_status(
        admin.delete(f"/clients/{hm_client_id}/deliverables/{approval_deliverable_id}"),
        200,
        "cleanup approval deliverable",
    )

    suffix = uuid4().hex[:8]
    created = admin.post(
        "/clients",
        json={
            "name": f"Smoke Cliente {suffix}",
            "organization_name": f"Smoke Organização {suffix}",
            "organization_slug": "internal",
            "status": "onboarding",
            "responsible_name": "Eduardo EG",
        },
    )
    assert_status(created, 201, "create client")
    created_body = created.json()
    created_client_id = created_body["client"]["id"]
    created_org_id = created_body["client"]["organization_id"]

    provisioned_workspaces = admin.get("/workspaces")
    assert_status(provisioned_workspaces, 200, "workspace provisioned with client")
    created_workspace = next(
        row for row in provisioned_workspaces.json() if row["organization_id"] == created_org_id
    )
    assert created_workspace["client_id"] == created_client_id
    assert created_workspace["tenant_organization_id"] == internal_workspace["tenant_organization_id"]

    hidden = client_user.get(f"/clients/{created_client_id}")
    assert_status(hidden, 404, "client cannot read another client")
    assert_status(
        client_user.get(f"/workspaces/{created_workspace['id']}"),
        404,
        "client cannot read another canonical workspace",
    )

    with connect() as conn:
        own_assigned_id = conn.execute(
            """
            insert into deliverables (organization_id, title, assignee_emails)
            values (%s, %s, jsonb_build_array(%s::text))
            returning id
            """,
            (hm_organization_id, f"Assigned HM {suffix}", CLIENT_EMAIL),
        ).fetchone()["id"]
        foreign_assigned_id = conn.execute(
            """
            insert into deliverables (organization_id, title, assignee_emails)
            values (%s, %s, jsonb_build_array(%s::text))
            returning id
            """,
            (created_org_id, f"Assigned Foreign {suffix}", CLIENT_EMAIL),
        ).fetchone()["id"]

    with connect() as conn:
        conn.execute(
            "update workspaces set status = 'archived', updated_at = now() where subject_organization_id = %s",
            (hm_organization_id,),
        )
    try:
        archived_workspaces = client_user.get("/workspaces")
        assert_status(archived_workspaces, 200, "archived workspace discovery")
        assert archived_workspaces.json() == [], "workspace arquivado deve sair da descoberta do cliente"
        assert_status(
            client_user.get(f"/clients/{hm_client_id}"),
            404,
            "workspace arquivado revoga adapter cliente",
        )
        assert_status(
            client_user.get(f"/clients/{hm_client_id}/files"),
            404,
            "workspace arquivado revoga files",
        )
        assert_status(
            client_user.get(f"/clients/{hm_client_id}/performance"),
            404,
            "workspace arquivado revoga performance",
        )
        assert_status(
            client_user.get(f"/integrations/{hm_organization_id}/kommo"),
            404,
            "workspace arquivado revoga Kommo",
        )
        archived_deliverables = client_user.get("/clients/deliverables/me")
        assert_status(archived_deliverables, 200, "archived workspace assigned deliverables")
        assert str(own_assigned_id) not in {row["id"] for row in archived_deliverables.json()}
    finally:
        with connect() as conn:
            conn.execute(
                "update workspaces set status = 'active', updated_at = now() where subject_organization_id = %s",
                (hm_organization_id,),
            )

    my_deliverables = client_user.get("/clients/deliverables/me")
    assert_status(my_deliverables, 200, "assigned deliverables respect workspace access")
    visible_assigned_ids = {row["id"] for row in my_deliverables.json()}
    assert str(own_assigned_id) in visible_assigned_ids
    assert str(foreign_assigned_id) not in visible_assigned_ids

    updated = admin.patch(
        f"/clients/{created_client_id}",
        json={"status": "active", "responsible_name": "CTO EG"},
    )
    assert_status(updated, 200, "update client")
    assert updated.json()["client"]["status"] == "active"

    artifact = admin.post(
        f"/clients/{created_client_id}/artifacts",
        json={
            "title": "Briefing smoke",
            "kind": "briefing",
            "visibility": "client",
            "content": "Conteúdo editável criado pelo smoke test.",
        },
    )
    assert_status(artifact, 201, "create artifact")
    artifact_id = artifact.json()["artifacts"][0]["id"]

    edited_artifact = admin.patch(
        f"/clients/{created_client_id}/artifacts/{artifact_id}",
        json={"title": "Briefing smoke editado"},
    )
    assert_status(edited_artifact, 200, "update artifact")

    deliverable = admin.post(
        f"/clients/{created_client_id}/deliverables",
        json={"title": "Entrega smoke", "status": "planned"},
    )
    assert_status(deliverable, 201, "create deliverable")
    deliverable_id = deliverable.json()["deliverables"][0]["id"]

    delivered = admin.patch(
        f"/clients/{created_client_id}/deliverables/{deliverable_id}",
        json={"status": "in_progress"},
    )
    assert_status(delivered, 200, "update deliverable")

    lead = admin.post(
        f"/clients/{created_client_id}/leads",
        json={
            "name": "Lead Smoke",
            "company": "Smoke Corp",
            "role_title": "CEO",
            "source": "LinkedIn",
            "stage": "new",
        },
    )
    assert_status(lead, 201, "create lead")
    invalid_lead = admin.post(f"/clients/{created_client_id}/leads", json={"company": "Sem nome"})
    assert_status(invalid_lead, 422, "invalid lead payload")
    lead_id = lead.json()[0]["id"]
    moved_lead = admin.patch(f"/clients/{created_client_id}/leads/{lead_id}", json={"stage": "meeting"})
    assert_status(moved_lead, 200, "update lead")
    client_leads = client_user.get(f"/clients/{created_client_id}/leads")
    assert_status(client_leads, 404, "client cannot read another client leads")

    finance = admin.post(
        f"/clients/{created_client_id}/finance",
        json={
            "kind": "invoice",
            "title": "Fatura smoke",
            "amount": 1200,
            "status": "open",
            "due_at": "2026-08-10",
        },
    )
    assert_status(finance, 201, "create financial record")
    finance_id = finance.json()[0]["id"]
    paid = admin.patch(f"/clients/{created_client_id}/finance/{finance_id}", json={"status": "paid", "paid_at": "2026-08-09"})
    assert_status(paid, 200, "update financial record")

    metric = admin.post(
        f"/clients/{created_client_id}/metrics",
        json={
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
            "channel": "LinkedIn",
            "metric": "impressions",
            "value": 1234,
            "source": "manual",
        },
    )
    assert_status(metric, 201, "create performance metric")
    metric_id = metric.json()[0]["id"]
    metric_update = admin.patch(f"/clients/{created_client_id}/metrics/{metric_id}", json={"value": 2345})
    assert_status(metric_update, 200, "update performance metric")

    with connect() as conn:
        conn.execute("delete from deliverables where id = %s", (own_assigned_id,))

    archived = admin.delete(f"/clients/{created_client_id}")
    assert_status(archived, 204, "archive client")
    assert archived.content == b"", "archive deve responder 204 sem corpo"
    assert_status(admin.get(f"/clients/{created_client_id}"), 404, "archived client is inaccessible")
    assert_status(
        admin.get(f"/workspaces/{created_workspace['id']}"),
        404,
        "archived workspace is inaccessible",
    )

    invalid_purge = admin.post(
        f"/clients/{created_client_id}/purge",
        json={"confirmation": "nome incorreto"},
    )
    assert_status(invalid_purge, 422, "purge requires exact client name")

    purged = admin.post(
        f"/clients/{created_client_id}/purge",
        json={"confirmation": f"Smoke Cliente {suffix}"},
    )
    assert_status(purged, 204, "purge archived client")
    assert purged.content == b"", "purge deve responder 204 sem corpo"
    assert_status(admin.get(f"/clients/{created_client_id}"), 404, "purged client is absent")

    with connect() as conn:
        purge_audit = conn.execute(
            """
            select organization_id, metadata
            from audit_logs
            where event_type = 'client.purged'
              and metadata ->> 'client_id' = %s
            order by created_at desc
            limit 1
            """,
            (str(created_client_id),),
        ).fetchone()
    assert purge_audit is not None, "purge precisa preservar evento de auditoria"
    assert purge_audit["organization_id"] is None, "auditoria preservada não deve reter FK removida"

    cleanup_initial_workspace()
    atexit.unregister(cleanup_initial_workspace)

    print("smoke ok")


if __name__ == "__main__":
    main()
