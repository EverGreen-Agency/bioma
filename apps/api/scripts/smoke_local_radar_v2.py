"""Smoke do Radar Local v2 + metas do Cockpit, contra o Postgres real.

Cobre: import de planilha (caminho sem custo de API), diff de rescan por
place_id (criou site / +avaliações / já é lead) e meta x realizado no rollup.
Limpa tudo o que cria.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    client = TestClient(app)
    assert_status(client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login")

    scan_ids: list[str] = []
    try:
        # 1) Import de planilha — sem tocar na Places API.
        first = client.post(
            "/backoffice/local-radar/scans/import",
            json={
                "niche": "smoke-padaria",
                "city": "smoke-city",
                "rows": [
                    {"name": "Padaria Smoke Um", "address": "Rua A, 1", "phone": "(34) 90000-0001",
                     "rating": 4.6, "rating_count": 12},
                    {"name": "Padaria Smoke Dois", "address": "Rua B, 2", "website": "https://dois.example.com",
                     "rating": 3.2, "rating_count": 40},
                ],
            },
        )
        assert_status(first, 201, "import")
        body = first.json()
        scan_ids.append(body["id"])
        assert body["source"] == "import", body
        assert body["prospect_count"] == 2, body

        by_name = {p["name"]: p for p in body["prospects"]}
        um = by_name["Padaria Smoke Um"]
        dois = by_name["Padaria Smoke Dois"]
        # Score deterministico: sem site (-35); telefone ok e 12 avaliacoes (>=10)
        # nao penalizam.
        assert um["presence_score"] == 65, um["presence_score"]
        assert um["presence_gaps"] == ["Sem site cadastrado no Google"], um["presence_gaps"]
        # Com site, mas sem telefone (-15) e nota 3.2 com >=5 avaliacoes (-20).
        assert dois["presence_score"] == 65, dois["presence_score"]
        assert set(dois["presence_gaps"]) == {"Sem telefone cadastrado no Google", "Nota baixa (3.2)"}, dois["presence_gaps"]
        assert um["changes"] == [], "primeiro scan nao tem historico"
        print(f"import OK — lacunas distintas: {um['presence_gaps']} vs {dois['presence_gaps']}")

        # Aprova o primeiro (cria lead) para o rescan detectar isso.
        assert_status(client.post(f"/backoffice/local-radar/prospects/{um['id']}/audit"), 200, "auditoria")
        approved = client.post(
            f"/backoffice/local-radar/prospects/{um['id']}/decision", json={"decision": "approved"}
        )
        assert_status(approved, 200, "aprovar")
        lead_id = approved.json()["lead_id"]
        assert lead_id, approved.json()

        # 2) Rescan: mesmo negócio, agora com site e mais avaliações.
        second = client.post(
            "/backoffice/local-radar/scans/import",
            json={
                "niche": "smoke-padaria",
                "city": "smoke-city",
                "rows": [
                    {"name": "Padaria Smoke Um", "address": "Rua A, 1", "phone": "(34) 90000-0001",
                     "website": "https://um.example.com", "rating": 4.6, "rating_count": 60},
                ],
            },
        )
        assert_status(second, 201, "rescan")
        scan_ids.append(second.json()["id"])
        rescanned = second.json()["prospects"][0]
        changes = rescanned["changes"]
        assert "Criou site desde o último scan" in changes, changes
        assert any("avaliações desde o último scan" in change for change in changes), changes
        assert any("Já é lead" in change for change in changes), changes
        # Ganhou site: score sobe de 50 para 100 (nenhuma lacuna restante).
        assert rescanned["presence_score"] == 100, rescanned["presence_score"]
        print(f"rescan OK — {len(changes)} sinais detectados: {changes}")

        # 3) Meta x realizado no rollup executivo.
        rollup = client.get("/backoffice/portfolio-performance?days=30")
        assert_status(rollup, 200, "rollup")
        rows = rollup.json()
        assert rows, "nenhum cliente na carteira"
        target_client = rows[0]
        assert "target_leads" in target_client, target_client

        updated = client.put(
            f"/backoffice/clients/{target_client['client_id']}/monthly-target",
            json={"target_leads": 40, "budget_cents": 500000},
        )
        assert_status(updated, 200, "definir meta")
        row = next(r for r in updated.json() if r["client_id"] == target_client["client_id"])
        assert row["target_leads"] == 40, row
        assert row["budget_cents"] == 500000, row
        print(f"meta OK — {row['client_name']}: meta 40 leads, realizado {row['total_leads']}")

        # Meta apagada volta a None (nao vira zero).
        cleared = client.put(
            f"/backoffice/clients/{target_client['client_id']}/monthly-target",
            json={"target_leads": None, "budget_cents": None},
        )
        assert_status(cleared, 200, "limpar meta")
        row = next(r for r in cleared.json() if r["client_id"] == target_client["client_id"])
        assert row["target_leads"] is None, row
        print("limpar meta OK — volta a null, nao a zero")

        assert_status(
            client.put("/backoffice/clients/00000000-0000-0000-0000-000000000000/monthly-target", json={}),
            404,
            "meta de cliente inexistente",
        )
        print("meta de cliente inexistente: 404 OK")
    finally:
        with connect() as conn:
            leads = conn.execute(
                "select distinct lead_id from local_radar_prospects where scan_id = any(%s) and lead_id is not null",
                (scan_ids,),
            ).fetchall() if scan_ids else []
            if scan_ids:
                conn.execute("delete from local_radar_scans where id = any(%s)", (scan_ids,))
            for row in leads:
                conn.execute("delete from leads where id = %s", (row["lead_id"],))
            conn.execute(
                "delete from monthly_targets where month = date_trunc('month', current_date)::date and target_leads is null and budget_micros is null"
            )
    print("limpeza OK — smoke_local_radar_v2 passou")


if __name__ == "__main__":
    main()
