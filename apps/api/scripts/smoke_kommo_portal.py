"""Smoke dos portais sem login: painel público e operação EG do Kommo.

O Kommo é substituído por um servidor falso em memória (`FakeKommo`), que registra
cada chamada. Assim o smoke valida o que o Bioma ESCREVERIA no CRM do cliente:

- o portal EG fecha sem chave e abre com ela; o painel público não devolve nome;
- deduplicação: o lead é vinculado ao principal antes de sair da duplicata, a
  duplicata é marcada e nenhum DELETE é emitido; reaplicar não repete nada;
- classificação: só campo vazio é preenchido, só com opção existente, e o estado
  vem do DDD;
- webhook: segredo errado é recusado e mensagem nova dispara a classificação.
"""

import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "SECRET_ENCRYPTION_KEY",
    __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode(),
)
os.environ["PORTAL_ADMIN_KEY"] = "chave-smoke-portal"
os.environ["DECISION_MODEL_API_KEY"] = ""

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.services import kommo_crm, kommo_portal
from bioma_api.worker_bridge import _ensure_worker_in_path

SLUG = "hm-conexoes"
KEY = {"Authorization": "Portal chave-smoke-portal"}
NOW = int(time.time())

PIPELINES = [
    {
        "id": 900,
        "name": "Inbound",
        "is_main": True,
        "_embedded": {"statuses": [{"id": 901, "name": "Primeiro atendimento", "sort": 10}]},
    }
]
CUSTOM_FIELDS = [
    {"id": 1, "name": "Segmento", "type": "select", "enums": [{"id": 11, "value": "Dental"}, {"id": 12, "value": "Medical"}]},
    {"id": 2, "name": "Produto de Interesse", "type": "multiselect", "enums": [{"id": 21, "value": "Galileana"}, {"id": 22, "value": "Prismática"}]},
    {"id": 3, "name": "UF", "type": "select", "enums": [{"id": 31, "value": "SP"}, {"id": 32, "value": "MG"}]},
]


def _lead(lead_id: int, contact_id: int, fields: list | None = None) -> dict:
    return {
        "id": lead_id,
        "name": "Dra. Nome Que Nao Pode Vazar",
        "created_at": NOW - lead_id,
        "updated_at": NOW,
        "pipeline_id": 900,
        "status_id": 901,
        "price": 0,
        "custom_fields_values": fields or [],
        "_embedded": {"contacts": [{"id": contact_id, "is_main": True}], "loss_reason": []},
    }


def _contact(contact_id: int, name: str, phone: str, lead_ids: list[int]) -> dict:
    return {
        "id": contact_id,
        "name": name,
        "created_at": NOW - contact_id,
        "custom_fields_values": [{"field_code": "PHONE", "values": [{"value": phone}]}],
        "_embedded": {"leads": [{"id": lead_id} for lead_id in lead_ids]},
    }


class FakeKommo:
    """Estado mínimo de uma conta Kommo e o registro das escritas recebidas."""

    def __init__(self) -> None:
        self.leads = {
            1: _lead(1, 11),
            2: _lead(2, 12, [{"field_id": 1, "field_name": "Segmento", "values": [{"value": "Medical"}]}]),
        }
        self.contacts = {
            11: _contact(11, "Carla Menezes", "(11) 98765-4321", [1]),
            12: _contact(12, "Carla Menezes", "+55 11 98765-4321", [2]),
        }
        self.messages = {
            1: [{"type": "incoming", "text": "Sou dentista, quero preço da lupa galileana", "created_at": 1}],
            2: [{"type": "incoming", "text": "Sou dentista e uso prismática", "created_at": 1}],
        }
        self.writes: list[tuple[str, str, object]] = []

    def request(self, method: str, path: str, **kwargs):
        params = kwargs.get("params")
        if method != "GET":
            self.writes.append((method, path, kwargs.get("json")))
        if method == "GET" and path == "/api/v4/account":
            return {"name": "Conta Smoke"}
        if method == "GET" and path == "/api/v4/leads/custom_fields":
            return {"_embedded": {"custom_fields": CUSTOM_FIELDS}}
        if method == "GET" and path == "/api/v4/contacts":
            ids = [int(value) for key, value in params if key == "filter[id][]"]
            return {"_embedded": {"contacts": [self.contacts[i] for i in ids if i in self.contacts]}}
        if method == "GET" and path.startswith("/api/v4/contacts/"):
            return self.contacts[int(path.rsplit("/", 1)[1])]
        if method == "GET" and path == "/api/v4/talks":
            lead_id = int(params["filter[entity_id][]"])
            return {"_embedded": {"talks": [{"talk_id": lead_id}]}}
        if method == "GET" and path.startswith("/api/v4/talks/"):
            return {"_embedded": {"messages": self.messages.get(int(path.split("/")[4]), [])}}
        if method == "GET" and path.startswith("/api/v4/leads/"):
            return self.leads[int(path.rsplit("/", 1)[1])]
        if method == "POST" and path.endswith("/link"):
            lead_id = int(path.split("/")[4])
            self.contacts[kwargs["json"][0]["to_entity_id"]]["_embedded"]["leads"].append({"id": lead_id})
            return {}
        if method == "POST" and path.endswith("/unlink"):
            lead_id = int(path.split("/")[4])
            contact = self.contacts[kwargs["json"][0]["to_entity_id"]]
            contact["_embedded"]["leads"] = [l for l in contact["_embedded"]["leads"] if l["id"] != lead_id]
            return {}
        if method == "PATCH" and path.startswith("/api/v4/contacts/"):
            self.contacts[int(path.rsplit("/", 1)[1])]["name"] = kwargs["json"]["name"]
            return {}
        if method == "PATCH" and path.startswith("/api/v4/leads/"):
            return {}
        if method == "POST" and path == "/api/v4/webhooks":
            return {"id": 4321}
        raise AssertionError(f"chamada inesperada ao Kommo: {method} {path}")

    def close(self) -> None:
        pass


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"{label} OK")


def main() -> None:
    client = TestClient(app)
    base = f"/portal/{SLUG}"
    fake = FakeKommo()

    with connect() as conn:
        org_id = conn.execute("select id from organizations where slug = %s", (SLUG,)).fetchone()["id"]
        previous = conn.execute(
            "select client_id, client_secret, access_token, subdomain from kommo_integrations where organization_id = %s",
            (org_id,),
        ).fetchone()

    def cleanup() -> None:
        with connect() as conn:
            for table in ("kommo_dedup_runs", "kommo_crm_snapshots", "kommo_lead_classifications", "kommo_webhooks", "kommo_integrations"):
                conn.execute(f"delete from {table} where organization_id = %s", (org_id,))
            conn.execute(
                "delete from audit_logs where organization_id = %s and metadata ->> 'via' = 'portal_eg'", (org_id,)
            )

    cleanup()
    real_api_class = kommo_portal.KommoApi
    real_fetch = kommo_crm._fetch_crm
    _ensure_worker_in_path()
    from bioma_worker.integrations.kommo_deduplication import KommoDeduplicationEngine

    real_fetch_contacts = KommoDeduplicationEngine.fetch_all_contacts

    async def fake_fetch_contacts(self, http_client, limit=250):
        return list(fake.contacts.values())

    kommo_portal.KommoApi = lambda subdomain, token: fake
    kommo_crm._fetch_crm = lambda subdomain, token: (PIPELINES, list(fake.leads.values()))
    KommoDeduplicationEngine.fetch_all_contacts = fake_fetch_contacts
    kommo_portal._THROTTLE_SECONDS = 0

    try:
        assert_status(client.get(f"{base}/eg/status"), 401, "portal EG sem chave")
        assert_status(client.get(f"{base}/eg/status", headers={"Authorization": "Portal errada"}), 401, "chave errada")
        assert_status(client.get("/portal/nao-existe/kommo/dashboard"), 404, "cliente inexistente")
        assert_status(client.post(f"{base}/eg/dedup/runs", headers=KEY), 409, "deduplicar sem conexão")

        connected = client.post(f"{base}/eg/kommo/connect", headers=KEY, json={"subdomain": "smoke", "access_token": "t"})
        assert_status(connected, 200, "conectar Kommo pelo portal")
        assert_status(client.post(f"{base}/eg/kommo/sync", headers=KEY), 200, "sincronizar pelo portal")

        public = client.get(f"{base}/kommo/dashboard")
        assert_status(public, 200, "painel público")
        check(public.json()["dashboard"]["totals"]["leads"] == 2 and "Nome Que Nao Pode Vazar" not in public.text,
              "painel público traz os 2 leads sem nome de pessoa")

        # --- Deduplicação
        run_id = client.post(f"{base}/eg/dedup/runs", headers=KEY).json()["id"]
        applied = client.post(f"{base}/eg/dedup/runs/{run_id}/apply", headers=KEY, json={"limit": 10})
        assert_status(applied, 200, "aplicar deduplicação")
        body = applied.json()
        check((body["processed"], body["leads_moved"], body["pending"], body["errors"]) == (1, 1, 0, []),
              "1 grupo unificado, 1 lead movido, nada pendente")
        methods = [(method, path) for method, path, _ in fake.writes]
        duplicate_id = next(cid for cid, contact in fake.contacts.items() if contact["name"].startswith("[DUPLICADO]"))
        master_id = 23 - duplicate_id
        moved_lead = 1 if duplicate_id == 11 else 2
        check(
            methods
            == [
                ("POST", f"/api/v4/leads/{moved_lead}/link"),
                ("POST", f"/api/v4/leads/{moved_lead}/unlink"),
                ("PATCH", f"/api/v4/contacts/{duplicate_id}"),
            ],
            "ordem das escritas: vincula ao principal, desvincula da duplicata, marca a duplicata",
        )
        check(not any(method == "DELETE" for method, _ in methods), "nenhum DELETE emitido")
        check({l["id"] for l in fake.contacts[master_id]["_embedded"]["leads"]} == {1, 2}
              and fake.contacts[duplicate_id]["_embedded"]["leads"] == [],
              "principal ficou com os dois leads e a duplicata sem nenhum")

        fake.writes.clear()
        again = client.post(f"{base}/eg/dedup/runs/{run_id}/apply", headers=KEY, json={"limit": 10}).json()
        check(again["processed"] == 0 and fake.writes == [], "reaplicar a mesma varredura não escreve nada")
        detail = client.get(f"{base}/eg/dedup/runs/{run_id}", headers=KEY).json()
        check(detail["progress"] == {"total": 1, "unified": 1, "errors": 0, "pending": 0}, "progresso registrado na varredura")

        # --- Classificação
        fake.writes.clear()
        simulated = client.post(f"{base}/eg/classification/batch", headers=KEY, json={"limit": 10, "write": False}).json()
        check(simulated["processed"] == 2 and fake.writes == [], "simulação lê os 2 leads e não escreve no Kommo")
        batch = client.post(f"{base}/eg/classification/batch", headers=KEY, json={"limit": 10})
        assert_status(batch, 200, "classificar lote")
        check((batch.json()["processed"], batch.json()["remaining"]) == (2, 0), "2 leads lidos, fila zerada")
        patches = {path: payload for method, path, payload in fake.writes if method == "PATCH"}
        lead1 = {item["field_id"]: item["values"] for item in patches["/api/v4/leads/1"]["custom_fields_values"]}
        lead2 = {item["field_id"]: item["values"] for item in patches["/api/v4/leads/2"]["custom_fields_values"]}
        check(lead1 == {1: [{"enum_id": 11}], 2: [{"enum_id": 21}], 3: [{"enum_id": 31}]},
              "lead vazio recebe segmento, produto e UF (pelo DDD), sempre com enum existente")
        check(1 not in lead2 and lead2 == {2: [{"enum_id": 22}], 3: [{"enum_id": 31}]},
              "campo já preenchido pelo time não é sobrescrito")
        results = client.get(f"{base}/eg/classification/results", headers=KEY).json()
        check(results["summary"]["fields_written"] == 5 and results["summary"]["engine"] == "regras",
              "resultado guarda 5 campos gravados e o motor usado")
        check("quero preço" not in str(results), "resultado não devolve o texto da conversa")

        # --- Webhook
        assert_status(client.post(f"{base}/eg/webhook", headers=KEY), 200, "ativar webhook")
        with connect() as conn:
            secret = conn.execute("select secret from kommo_webhooks where organization_id = %s", (org_id,)).fetchone()["secret"]
            conn.execute("delete from kommo_lead_classifications where organization_id = %s and lead_id = 1", (org_id,))
        registered = next(payload for method, path, payload in fake.writes if path == "/api/v4/webhooks")
        check(registered["settings"] == ["add_message", "add_lead"] and registered["destination"].endswith(secret),
              "webhook registrado no Kommo para mensagem e lead novos")
        assert_status(client.post(f"{base}/kommo/webhook/segredo-errado", data={"x": "1"}), 404, "webhook com segredo errado")
        fake.writes.clear()
        hook = client.post(
            f"{base}/kommo/webhook/{secret}",
            data={"message[add][0][entity_id]": "1", "message[add][0][entity_type]": "lead", "message[add][0][text]": "oi"},
        )
        assert_status(hook, 200, "webhook de mensagem")
        with connect() as conn:
            row = conn.execute(
                "select trigger from kommo_lead_classifications where organization_id = %s and lead_id = 1", (org_id,)
            ).fetchone()
        check(row is not None and row["trigger"] == "webhook", "mensagem nova reclassificou o lead pelo webhook")
    finally:
        kommo_portal.KommoApi = real_api_class
        kommo_crm._fetch_crm = real_fetch
        KommoDeduplicationEngine.fetch_all_contacts = real_fetch_contacts
        cleanup()
        if previous:
            with connect() as conn:
                conn.execute(
                    """
                    insert into kommo_integrations (organization_id, client_id, client_secret, access_token, subdomain)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (org_id, previous["client_id"], previous["client_secret"], previous["access_token"], previous["subdomain"]),
                )

    print("limpeza OK — smoke_kommo_portal passou")


if __name__ == "__main__":
    main()
