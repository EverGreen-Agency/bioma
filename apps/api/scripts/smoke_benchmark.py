"""Smoke test do benchmark público + toggle.

Valida, contra o banco de dev (precisa das migrations aplicadas):
- endpoint público é acessível SEM sessão;
- toggle em_breve -> payload vazio;
- k-anonimato: segmento com base < min_sample não aparece;
- toggle ao_vivo + base suficiente -> agregado anonimizado aparece;
- só EG admin lê/vira o toggle.

Uso: `python scripts/smoke_benchmark.py` (com o Postgres do Bioma no ar).
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uuid import uuid4

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "henrique@hmconexoes.com.br"
PASSWORD = "senha-dev-123"


def assert_status(response, expected, label):
    assert response.status_code == expected, f"{label}: esperado {expected}, veio {response.status_code} — {response.text}"


def login(client: TestClient, email: str) -> None:
    assert_status(client.post("/auth/login", json={"email": email, "password": PASSWORD}), 200, f"login {email}")


def _seed_segment(segment: str, n: int) -> list[str]:
    """Cria n organizações consentidas no segmento, cada uma com 3 scores."""
    org_ids: list[str] = []
    with connect() as conn:
        for i in range(n):
            org = conn.execute(
                """
                insert into organizations (name, slug, type, benchmark_segment, benchmark_consent)
                values (%s, %s, 'client', %s, true)
                returning id
                """,
                (f"Bench {segment} {i} {uuid4().hex[:6]}", f"bench-{uuid4().hex[:10]}", segment),
            ).fetchone()["id"]
            org_ids.append(str(org))
            for pillar, score in (("oferta", 6.0), ("demanda", 5.0), ("conversao", 7.0)):
                conn.execute(
                    "insert into raio_x_scores (organization_id, pillar, score) values (%s, %s, %s)",
                    (org, pillar, score),
                )
    return org_ids


def _cleanup(org_ids: list[str]) -> None:
    if not org_ids:
        return
    with connect() as conn:
        conn.execute("delete from organizations where id = any(%s::uuid[])", (org_ids,))


def _set_toggle(status: str) -> None:
    with connect() as conn:
        conn.execute(
            "update benchmark_settings set status = %s, updated_at = now() where id = true",
            (status,),
        )


def main() -> None:
    guest = TestClient(app)
    admin = TestClient(app)
    client_user = TestClient(app)
    login(admin, ADMIN_EMAIL)
    login(client_user, CLIENT_EMAIL)

    original = admin.get("/benchmark/settings")
    assert_status(original, 200, "admin lê settings")
    original_status = original.json()["status"]
    min_sample = original.json()["min_sample"]

    # público é acessível sem sessão
    assert_status(guest.get("/public/benchmark"), 200, "público sem sessão")
    # cliente não pode ler/virar o toggle
    assert_status(client_user.get("/benchmark/settings"), 403, "cliente não lê settings")
    assert_status(client_user.patch("/benchmark/settings", json={"status": "ao_vivo"}), 403, "cliente não vira toggle")

    big = small = []
    try:
        # em_breve => vazio
        _set_toggle("em_breve")
        p = guest.get("/public/benchmark").json()
        assert p["status"] == "em_breve" and p["segments"] == [], "em_breve deve vir vazio"

        seg_big = f"Bench-Big-{uuid4().hex[:6]}"
        seg_small = f"Bench-Small-{uuid4().hex[:6]}"
        big = _seed_segment(seg_big, min_sample)  # atinge o k-anonimato
        small = _seed_segment(seg_small, max(min_sample - 1, 2))  # fica abaixo

        # vira ao_vivo pelo endpoint admin (o mesmo caminho que o EG usa)
        assert_status(admin.patch("/benchmark/settings", json={"status": "ao_vivo"}), 200, "admin vira ao_vivo")

        p = guest.get("/public/benchmark").json()
        assert p["status"] == "ao_vivo", p["status"]
        segs = {s["segment"]: s for s in p["segments"]}
        assert seg_big in segs, "segmento com base suficiente deve aparecer"
        assert seg_small not in segs, "segmento abaixo do k-anonimato NÃO pode aparecer"
        big_seg = segs[seg_big]
        assert big_seg["sampleSize"] == min_sample
        assert big_seg["overallMedian"] == 6.0, big_seg["overallMedian"]  # (6+5+7)/3
        assert {x["key"] for x in big_seg["pillars"]} == {"oferta", "demanda", "conversao"}
        print("smoke benchmark ok")
    finally:
        _cleanup(big)
        _cleanup(small)
        _set_toggle(original_status)


if __name__ == "__main__":
    main()
