"""Smoke do Radar Local contra o Postgres real.

Sem GOOGLE_PLACES_API_KEY o scan deve falhar alto (422) — nunca inventar
negócios. O restante do fluxo (auditoria em prévia, mensagem, decisão com
aprovação humana, envio simulado) é testado com um prospect inserido
diretamente e limpo no final.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from bioma_api.db import connect
from bioma_api.main import app

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    client = TestClient(app)
    response = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    assert_status(response, 200, "login admin")

    # 1. Sem chave do Places: 422 honesto, nada gravado.
    from bioma_api.worker_bridge import _ensure_worker_in_path
    _ensure_worker_in_path()
    from bioma_worker.config import get_settings as worker_settings
    if not worker_settings().google_places_api_key:
        response = client.post(
            "/backoffice/local-radar/scans",
            json={"niche": "clínica odontológica", "city": "Uberlândia", "limit": 5},
        )
        assert_status(response, 422, "scan sem GOOGLE_PLACES_API_KEY")
        assert "GOOGLE_PLACES_API_KEY" in response.json()["detail"], response.text
        print("scan sem chave: 422 honesto OK")
    else:
        response = client.post(
            "/backoffice/local-radar/scans",
            json={"niche": "clínica odontológica", "city": "Uberlândia", "limit": 5},
        )
        assert_status(response, 201, "scan com chave real")
        print(f"scan live: {response.json()['prospect_count']} prospects")

    # 2. Fluxo de revisão com prospect inserido manualmente (dados de teste).
    with connect() as conn:
        scan_row = conn.execute(
            """
            insert into local_radar_scans (niche, city, query_text, prospect_count)
            values ('smoke', 'smoke', 'smoke radar', 1) returning id
            """,
        ).fetchone()
        scan_id = scan_row["id"]
        prospect_row = conn.execute(
            """
            insert into local_radar_prospects (
              scan_id, place_id, name, address, phone, presence_score, presence_gaps
            )
            values (%s, 'smoke-place-1', 'Padaria Smoke', 'Rua Teste, 1', '(34) 99999-0000', 50, %s)
            returning id
            """,
            (scan_id, Jsonb(["Sem site cadastrado no Google"])),
        ).fetchone()
        prospect_id = str(prospect_row["id"])

    try:
        # aprovar sem auditoria: 422
        response = client.post(
            f"/backoffice/local-radar/prospects/{prospect_id}/decision", json={"decision": "approved"}
        )
        assert_status(response, 422, "aprovar sem auditoria")
        print("aprovar sem auditoria: 422 OK")

        # auditoria (preview sem OPENAI_API_KEY, live com)
        response = client.post(f"/backoffice/local-radar/prospects/{prospect_id}/audit")
        assert_status(response, 200, "auditoria")
        body = response.json()
        assert body["review_status"] == "audited", body
        assert body["audit_mode"] in ("live", "preview"), body
        assert body["outreach_message"], body
        print(f"auditoria OK (modo={body['audit_mode']})")

        # enviar sem aprovação: 409
        response = client.post(
            f"/backoffice/local-radar/prospects/{prospect_id}/send", json={"provider_type": "evolution"}
        )
        assert_status(response, 409, "enviar sem aprovação")
        print("enviar sem aprovação humana: 409 OK")

        # editar mensagem
        response = client.patch(
            f"/backoffice/local-radar/prospects/{prospect_id}/message",
            json={"message": "Mensagem revisada pelo humano."},
        )
        assert_status(response, 200, "editar mensagem")

        # aprovar: cria lead no CRM da EG
        response = client.post(
            f"/backoffice/local-radar/prospects/{prospect_id}/decision", json={"decision": "approved"}
        )
        assert_status(response, 200, "aprovar")
        approved = response.json()
        assert approved["review_status"] == "approved", approved
        assert approved["lead_id"], "aprovação deveria ter criado lead na EG"
        print(f"aprovado + lead criado: {approved['lead_id']}")

        # enviar (provider evolution sem credencial → simulated, prospect NÃO vira sent)
        response = client.post(
            f"/backoffice/local-radar/prospects/{prospect_id}/send", json={"provider_type": "evolution"}
        )
        assert_status(response, 200, "envio")
        sent = response.json()
        assert sent["send_status"] in ("sent", "simulated", "failed"), sent
        if sent["send_status"] == "sent":
            assert sent["prospect"]["review_status"] == "sent", sent
            print("envio real OK")
        else:
            # simulated (sem credencial) ou failed (provider fora do ar): a
            # mensagem não chegou, então o prospect NÃO pode virar 'sent'.
            assert sent["prospect"]["review_status"] == "approved", sent
            assert sent["detail"], sent
            print(f"envio {sent['send_status']} não marcou como enviado: OK ({sent['detail'][:80]})")

        # listagem
        response = client.get("/backoffice/local-radar/scans")
        assert_status(response, 200, "listar scans")
        response = client.get(f"/backoffice/local-radar/scans/{scan_id}")
        assert_status(response, 200, "detalhe do scan")
        assert len(response.json()["prospects"]) == 1
    finally:
        with connect() as conn:
            row = conn.execute(
                "select lead_id from local_radar_prospects where id = %s", (prospect_id,)
            ).fetchone()
            conn.execute("delete from local_radar_scans where id = %s", (scan_id,))
            if row and row["lead_id"]:
                conn.execute("delete from leads where id = %s", (row["lead_id"],))
            conn.execute("delete from workspace_whatsapp_message_logs where to_number = '34999990000'")
    print("limpeza OK — smoke_local_radar passou")


if __name__ == "__main__":
    main()
