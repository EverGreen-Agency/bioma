from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect
from bioma_api.config import get_settings
from bioma_api.security import hash_password
from bioma_api.repositories import workspaces as workspaces_repo
from performance_seed import seed_performance


DEV_PASSWORD = "senha-dev-123"


def upsert_org(conn, name: str, slug: str, org_type: str):
    row = conn.execute("select id from organizations where slug = %s", (slug,)).fetchone()
    if row:
        conn.execute(
            "update organizations set name = %s, type = %s, updated_at = now() where id = %s",
            (name, org_type, row["id"]),
        )
        return row["id"]
    return conn.execute(
        "insert into organizations (name, slug, type) values (%s, %s, %s) returning id",
        (name, slug, org_type),
    ).fetchone()["id"]


def upsert_user(conn, email: str, display_name: str):
    password_hash = hash_password(DEV_PASSWORD)
    row = conn.execute("select id from users where lower(email) = %s", (email.lower(),)).fetchone()
    if row:
        conn.execute(
            """
            update users
            set display_name = %s, password_hash = %s, is_active = true, updated_at = now()
            where id = %s
            """,
            (display_name, password_hash, row["id"]),
        )
        return row["id"]
    return conn.execute(
        """
        insert into users (email, display_name, password_hash)
        values (%s, %s, %s)
        returning id
        """,
        (email.lower(), display_name, password_hash),
    ).fetchone()["id"]


def upsert_membership(conn, user_id, organization_id, role: str) -> None:
    conn.execute(
        """
        insert into memberships (user_id, organization_id, role)
        values (%s, %s, %s)
        on conflict (user_id, organization_id)
        do update set role = excluded.role
        """,
        (user_id, organization_id, role),
    )


def upsert_artifact(
    conn,
    organization_id,
    title: str,
    kind: str,
    visibility: str,
    content: str,
    url: str | None = None,
) -> None:
    row = conn.execute(
        """
        select id from artifacts
        where organization_id = %s and title = %s and kind = %s
        """,
        (organization_id, title, kind),
    ).fetchone()
    if row:
        conn.execute(
            """
            update artifacts
            set visibility = %s, content = %s, url = %s
            where id = %s
            """,
            (visibility, content, url, row["id"]),
        )
        return
    conn.execute(
        """
        insert into artifacts (organization_id, title, kind, visibility, content, url)
        values (%s, %s, %s, %s, %s, %s)
        """,
        (organization_id, title, kind, visibility, content, url),
    )


def upsert_deliverable(
    conn,
    organization_id,
    title: str,
    status: str,
    due_at: str | None = None,
):
    row = conn.execute(
        """
        select id from deliverables
        where organization_id = %s and title = %s
        """,
        (organization_id, title),
    ).fetchone()
    if row:
        conn.execute(
            """
            update deliverables
            set status = %s, due_at = %s, updated_at = now()
            where id = %s
            """,
            (status, due_at, row["id"]),
        )
        return row["id"]
    return conn.execute(
        """
        insert into deliverables (organization_id, title, status, due_at)
        values (%s, %s, %s, %s)
        returning id
        """,
        (organization_id, title, status, due_at),
    ).fetchone()["id"]


def ensure_pending_approval(conn, organization_id, deliverable_id, requested_by, comment: str) -> None:
    row = conn.execute(
        """
        select id from approvals
        where organization_id = %s and deliverable_id = %s
        order by created_at asc
        limit 1
        """,
        (organization_id, deliverable_id),
    ).fetchone()
    if row:
        conn.execute(
            """
            update approvals
            set status = 'pending', comment = %s, requested_by = %s, decided_by = null, decided_at = null
            where id = %s
            """,
            (comment, requested_by, row["id"]),
        )
        conn.execute(
            """
            delete from approvals
            where organization_id = %s and deliverable_id = %s and id <> %s
            """,
            (organization_id, deliverable_id, row["id"]),
        )
        return
    conn.execute(
        """
        insert into approvals (organization_id, deliverable_id, requested_by, status, comment)
        values (%s, %s, %s, 'pending', %s)
        """,
        (organization_id, deliverable_id, requested_by, comment),
    )


def upsert_lead(conn, organization_id, name: str, company: str, role_title: str, stage: str, source: str) -> None:
    row = conn.execute(
        """
        select id from leads
        where organization_id = %s and name = %s and company = %s
        """,
        (organization_id, name, company),
    ).fetchone()
    if row:
        conn.execute(
            """
            update leads
            set role_title = %s, stage = %s, source = %s, updated_at = now()
            where id = %s
            """,
            (role_title, stage, source, row["id"]),
        )
        return
    conn.execute(
        """
        insert into leads (organization_id, name, company, role_title, stage, source)
        values (%s, %s, %s, %s, %s, %s)
        """,
        (organization_id, name, company, role_title, stage, source),
    )


def upsert_financial_record(
    conn,
    organization_id,
    title: str,
    kind: str,
    amount: float,
    status: str,
    due_at: str | None,
) -> None:
    row = conn.execute(
        """
        select id from financial_records
        where organization_id = %s and title = %s
        """,
        (organization_id, title),
    ).fetchone()
    if row:
        conn.execute(
            """
            update financial_records
            set kind = %s, amount = %s, status = %s, due_at = %s, updated_at = now()
            where id = %s
            """,
            (kind, amount, status, due_at, row["id"]),
        )
        return
    conn.execute(
        """
        insert into financial_records (organization_id, title, kind, amount, status, due_at)
        values (%s, %s, %s, %s, %s, %s)
        """,
        (organization_id, title, kind, amount, status, due_at),
    )


def upsert_performance_metric(
    conn,
    organization_id,
    period_start: str,
    period_end: str,
    channel: str,
    metric: str,
    value: float,
    source: str = "manual",
) -> None:
    row = conn.execute(
        """
        select id from performance_metrics
        where organization_id = %s and period_start = %s and period_end = %s
          and channel = %s and metric = %s
        """,
        (organization_id, period_start, period_end, channel, metric),
    ).fetchone()
    if row:
        conn.execute(
            """
            update performance_metrics
            set value = %s, source = %s, captured_at = now()
            where id = %s
            """,
            (value, source, row["id"]),
        )
        return
    conn.execute(
        """
        insert into performance_metrics (organization_id, period_start, period_end, channel, metric, value, source)
        values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (organization_id, period_start, period_end, channel, metric, value, source),
    )


def main() -> None:
    settings = get_settings()
    allow_non_local = os.getenv("ALLOW_DEV_SEED", "").lower() in {"1", "true", "yes"}
    if settings.app_env != "local" and not allow_non_local:
        raise RuntimeError(
            "seed_dev.py é bloqueado fora de local. Use ALLOW_DEV_SEED=true apenas em staging controlado."
        )

    with connect() as conn:
        eg_id = upsert_org(conn, "EverGreen", "eg", "eg")
        hm_id = upsert_org(conn, "HM Conexões Poderosas", "hm-conexoes", "client")

        conn.execute(
            "update organizations set parent_organization_id = %s, updated_at = now() where id = %s",
            (eg_id, hm_id),
        )
        workspaces_repo.provision_agency_workspace(conn, eg_id, "Operação EG")

        # A org EG opera a plataforma: todos os módulos habilitados
        # (clientes ficam no default hub/content/files da migration 0005).
        conn.execute(
            """
            update organizations
            set enabled_modules = '["hub", "content", "files", "commercial", "analytics", "integrations", "engineering"]'::jsonb
            where id = %s
            """,
            (eg_id,),
        )

        admin_id = upsert_user(conn, "eduardo@evergreengrowth.com.br", "Eduardo EG")
        client_id = upsert_user(conn, "henrique@hmconexoes.com.br", "Henrique Miranda")

        upsert_membership(conn, admin_id, eg_id, "eg_admin")
        upsert_membership(conn, admin_id, hm_id, "eg_admin")
        upsert_membership(conn, client_id, hm_id, "client_user")

        conn.execute(
            """
            insert into clients (organization_id, name, status, responsible_name)
            values (%s, 'HM Conexões Poderosas', 'onboarding', 'Eduardo EG')
            on conflict (organization_id)
            do update set
              name = excluded.name,
              status = excluded.status,
              responsible_name = excluded.responsible_name
            """,
            (hm_id,),
        )
        hm_client_id = conn.execute(
            "select id from clients where organization_id = %s",
            (hm_id,),
        ).fetchone()["id"]
        workspaces_repo.provision_client_workspace(
            conn,
            eg_id,
            hm_id,
            "HM Conexões Poderosas",
            "hm-conexoes",
        )

        upsert_artifact(
            conn,
            hm_id,
            "Briefing estratégico HM",
            "briefing",
            "client",
            "Direcionamento inicial para posicionamento, relacionamento e conteúdo no LinkedIn.",
        )
        upsert_artifact(
            conn,
            hm_id,
            "Brand book v0",
            "brand_book",
            "client",
            "Base de tom de voz, mensagens-chave e pilares editoriais para validação do cliente.",
        )
        upsert_artifact(
            conn,
            hm_id,
            "Calendário editorial inicial",
            "calendar",
            "client",
            "Primeira visão editável de pautas e entregas. Métricas entram apenas quando houver fonte real.",
        )
        briefing_id = upsert_deliverable(
            conn,
            hm_id,
            "Aprovar briefing estratégico",
            "waiting_approval",
            "2026-07-12 18:00:00-03",
        )
        upsert_deliverable(
            conn,
            hm_id,
            "Configurar hub do cliente",
            "in_progress",
            "2026-07-15 18:00:00-03",
        )
        upsert_deliverable(
            conn,
            hm_id,
            "Publicar calendário editorial inicial",
            "planned",
            "2026-07-18 18:00:00-03",
        )
        ensure_pending_approval(
            conn,
            hm_id,
            briefing_id,
            admin_id,
            "Cliente precisa validar antes de seguir para brand book e calendário.",
        )
        upsert_lead(conn, hm_id, "Rafael Almeida", "TechGrowth", "CIO", "new", "LinkedIn")
        upsert_lead(conn, hm_id, "Camila Ferreira", "InnovaBrand", "CMO", "qualifying", "Indicação")
        upsert_lead(conn, hm_id, "João Silva", "DataMakers", "CEO", "meeting", "LinkedIn")
        upsert_lead(conn, hm_id, "Ana Paula Santos", "HealthPlus", "CEO", "proposal", "Evento")
        upsert_lead(conn, hm_id, "Victor Hugo", "Drive Tech", "CEO", "won", "LinkedIn")
        upsert_financial_record(conn, hm_id, "Contrato HM - plano empresarial", "contract", 4500, "open", "2026-07-30")
        upsert_financial_record(conn, hm_id, "Fatura julho", "invoice", 4500, "open", "2026-07-15")
        upsert_performance_metric(conn, hm_id, "2026-06-01", "2026-06-30", "LinkedIn", "impressions", 753666)
        upsert_performance_metric(conn, hm_id, "2026-06-01", "2026-06-30", "LinkedIn", "followers", 8642)
        upsert_performance_metric(conn, hm_id, "2026-06-01", "2026-06-30", "CRM", "qualified_meetings", 18)
        seed_performance(conn, hm_client_id, hm_id)

    print("seed ok")
    print("admin: eduardo@evergreengrowth.com.br / senha-dev-123")
    print("cliente: henrique@hmconexoes.com.br / senha-dev-123")


if __name__ == "__main__":
    main()
