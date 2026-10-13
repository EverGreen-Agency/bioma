"""Smoke do painel de dados reais e da deduplicação do Kommo.

A rede do Kommo é substituída por leituras fixas: o que se valida aqui é o caminho
do Bioma (gates de acesso, snapshot sem dado pessoal, histórico de varreduras,
paginação e mascaramento do motivo), não a API do Kommo.

Valida: anônimo 401; cliente sem módulo comercial 403; sincronizar e deduplicar
são só de EG admin; sem credencial responde 409; painel nulo antes da primeira
sincronização; depois dela os números batem e nenhum nome vai para o snapshot;
a varredura fica no histórico e o detalhe não devolve o telefone do motivo.
"""

import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Chave de cifra ANTES de importar o app (settings é cacheado por processo).
os.environ.setdefault(
    "SECRET_ENCRYPTION_KEY",
    __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode(),
)

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.services import kommo_crm as kommo_crm_service
from bioma_api.worker_bridge import _ensure_worker_in_path

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "henrique@hmconexoes.com.br"
DEV_PASSWORD = "senha-dev-123"

NOW = int(time.time())
DAY = 86400

PIPELINES = [
    {
        "id": 900,
        "name": "Inbound",
        "is_main": True,
        "_embedded": {
            "statuses": [
                {"id": 901, "name": "Primeiro atendimento", "sort": 10},
                {"id": 142, "name": "Venda ganha", "sort": 20},
                {"id": 143, "name": "Venda perdida", "sort": 30},
            ]
        },
    }
]


def _lead(lead_id: int, days_ago: int, status_id: int = 901, price: int = 0, fields: dict | None = None) -> dict:
    return {
        "id": lead_id,
        "name": "Dra. Nome Que Nao Pode Vazar",
        "created_at": NOW - days_ago * DAY,
        "updated_at": NOW - days_ago * DAY,
        "closed_at": None,
        "pipeline_id": 900,
        "status_id": status_id,
        "price": price,
        "custom_fields_values": [
            {"field_name": name, "values": [{"value": value}]} for name, value in (fields or {}).items()
        ],
        "_embedded": {"loss_reason": []},
    }


LEADS = [
    _lead(1, 2, fields={"Origem do lead": "Google Ads", "Segmento": "Dental", "UF": "SP"}),
    _lead(2, 5, fields={"Origem do lead": "Indicação", "Segmento": "Medical"}),
    _lead(3, 20, status_id=142, price=18000, fields={"Origem do lead": "Google Ads"}),
    _lead(4, 200, status_id=143),
]


def _contact(contact_id: int, name: str, phone: str, lead_ids: list[int]) -> dict:
    return {
        "id": contact_id,
        "name": name,
        "created_at": NOW - contact_id,
        "custom_fields_values": [{"field_code": "PHONE", "values": [{"value": phone}]}],
        "_embedded": {"leads": [{"id": lead_id} for lead_id in lead_ids]},
    }


CONTACTS = [
    _contact(11, "Carla Menezes", "(11) 98765-4321", [1]),
    _contact(12, "Carla Menezes", "+55 11 98765-4321", [2]),
    _contact(13, "Otavio Brandao", "(31) 3456-7890", []),
]


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"{label} OK")


def main() -> None:
    admin = TestClient(app)
    client_user = TestClient(app)
    anon = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": DEV_PASSWORD}), 200, "login admin")
    assert_status(
        client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": DEV_PASSWORD}), 200, "login cliente"
    )

    clients = admin.get("/clients").json()
    org_id = next(c for c in clients if c["organization_slug"] == "hm-conexoes")["organization_id"]
    base = f"/integrations/{org_id}/kommo"

    with connect() as conn:
        previous_integration = conn.execute(
            "select client_id, client_secret, access_token, subdomain from kommo_integrations where organization_id = %s",
            (org_id,),
        ).fetchone()
        conn.execute("delete from kommo_integrations where organization_id = %s", (org_id,))
        conn.execute("delete from kommo_crm_snapshots where organization_id = %s", (org_id,))

    real_fetch = kommo_crm_service._fetch_crm
    _ensure_worker_in_path()
    from bioma_worker.integrations.kommo_deduplication import KommoDeduplicationEngine

    real_fetch_contacts = KommoDeduplicationEngine.fetch_all_contacts

    async def fake_fetch_contacts(self, client, limit=250):
        return CONTACTS

    try:
        assert_status(anon.get(f"{base}/dashboard"), 401, "painel anônimo")
        assert_status(client_user.get(f"{base}/dashboard"), 403, "painel cliente sem módulo comercial")
        assert_status(client_user.post(f"{base}/dashboard/sync"), 403, "cliente não sincroniza")
        assert_status(client_user.post(f"{base}/dedup/runs"), 403, "cliente não roda deduplicação")
        assert_status(admin.get(f"{base}/dashboard?days=7"), 422, "período inválido")

        empty = admin.get(f"{base}/dashboard")
        assert_status(empty, 200, "painel sem conexão")
        check(empty.json() == {"configured": False, "subdomain": None, "fetched_at": None, "dashboard": None},
              "sem conexão o painel vem nulo, sem número inventado")
        assert_status(admin.post(f"{base}/dashboard/sync"), 409, "sincronizar sem credencial")
        assert_status(admin.post(f"{base}/dedup/runs"), 409, "deduplicar sem credencial")

        assert_status(
            admin.post(base, json={"client_id": "id", "client_secret": "s", "access_token": "t", "subdomain": "smoke"}),
            200,
            "admin salva credencial",
        )
        kommo_crm_service._fetch_crm = lambda subdomain, token: (PIPELINES, LEADS)
        KommoDeduplicationEngine.fetch_all_contacts = fake_fetch_contacts

        synced = admin.post(f"{base}/dashboard/sync?days=30")
        assert_status(synced, 200, "sincronizar")
        totals = synced.json()["dashboard"]["totals"]
        check((totals["leads"], totals["leads_all_time"], totals["won"], totals["won_value"]) == (3, 4, 1, 18000.0),
              "recorte de 30 dias: 3 de 4 leads, 1 venda ganha de R$ 18.000")

        with connect() as conn:
            stored = conn.execute(
                "select leads::text as leads, leads_count from kommo_crm_snapshots where organization_id = %s", (org_id,)
            ).fetchone()
        check(stored["leads_count"] == 4 and "Nome Que Nao Pode Vazar" not in stored["leads"],
              "snapshot guarda os 4 leads sem nome de pessoa")

        all_time = admin.get(f"{base}/dashboard?days=0").json()["dashboard"]
        origem = next(d for d in all_time["dimensions"] if d["key"] == "origem")
        check(all_time["totals"]["leads"] == 4 and origem["items"][0] == {"label": "Google Ads", "count": 2, "share": 2 / 3},
              "histórico completo lê do snapshot, sem nova chamada ao Kommo")

        run = admin.post(f"{base}/dedup/runs")
        assert_status(run, 200, "varredura de duplicatas")
        summary = run.json()
        check((summary["contacts_scanned"], summary["clusters_count"], summary["leads_to_reassign"]) == (3, 1, 1),
              "varredura: 3 contatos, 1 par duplicado, 1 lead a mover")

        runs = admin.get(f"{base}/dedup/runs")
        assert_status(runs, 200, "histórico de varreduras")
        check(runs.json()[0]["id"] == summary["id"], "varredura aparece no histórico")

        detail = admin.get(f"{base}/dedup/runs/{summary['id']}?only_with_leads=true")
        assert_status(detail, 200, "detalhe da varredura")
        body = detail.json()
        cluster = body["clusters"][0]
        check(body["total_clusters"] == 1 and cluster["match_kind"] == "Mesmo telefone" and "br_" not in detail.text,
              "detalhe classifica o motivo e não devolve o telefone")
        check(cluster["master_name"] == "Carla Menezes" and len(cluster["duplicate_contacts"]) == 1,
              "par traz contato principal e a duplicata")
        assert_status(client_user.get(f"{base}/dedup/runs/{summary['id']}"), 403, "cliente não lê relatório")
    finally:
        kommo_crm_service._fetch_crm = real_fetch
        KommoDeduplicationEngine.fetch_all_contacts = real_fetch_contacts
        with connect() as conn:
            conn.execute("delete from kommo_dedup_runs where organization_id = %s", (org_id,))
            conn.execute("delete from kommo_crm_snapshots where organization_id = %s", (org_id,))
            conn.execute("delete from kommo_integrations where organization_id = %s", (org_id,))
            conn.execute(
                "delete from audit_logs where organization_id = %s and event_type in ('kommo.crm_synced', 'kommo.dedup_simulated')",
                (org_id,),
            )
            if previous_integration:
                conn.execute(
                    """
                    insert into kommo_integrations (organization_id, client_id, client_secret, access_token, subdomain)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (
                        org_id,
                        previous_integration["client_id"],
                        previous_integration["client_secret"],
                        previous_integration["access_token"],
                        previous_integration["subdomain"],
                    ),
                )

    print("limpeza OK — smoke_kommo_crm passou")


if __name__ == "__main__":
    main()
