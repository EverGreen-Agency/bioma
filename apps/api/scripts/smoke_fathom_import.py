"""Smoke do adaptador Fathom no copiloto de vendas, contra o Postgres real.

Sem FATHOM_API_KEY, os dois endpoints devem falhar alto (422) com a mensagem
real. Com chave, importa de verdade. A regra de consentimento é testada nos dois
casos: sem consentimento registrado, o import é 409 antes de qualquer chamada
externa. A idempotência é testada injetando segmentos direto no repositório.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.repositories import sales_copilot as copilot_repo

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def main() -> None:
    client = TestClient(app)
    assert_status(client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login")

    from bioma_api.worker_bridge import _ensure_worker_in_path

    _ensure_worker_in_path()
    from bioma_worker.config import get_settings as worker_settings

    has_key = bool(worker_settings().fathom_api_key)

    listing = client.get("/backoffice/sales-copilot/fathom/meetings?limit=5")
    if has_key:
        assert_status(listing, 200, "listar reunioes do Fathom")
        print(f"listagem live OK — {len(listing.json())} reuniao(oes)")
    else:
        assert_status(listing, 422, "listar sem FATHOM_API_KEY")
        assert "FATHOM_API_KEY" in listing.json()["detail"], listing.text
        print("listagem sem chave: 422 honesto OK")

    # Sessão de teste para validar as regras de guarda.
    session = client.post(
        "/backoffice/sales-copilot",
        json={"title": "Smoke Fathom", "objective": "validar import"},
    )
    assert_status(session, 201, "criar sessao")
    session_id = session.json()["id"]

    try:
        # Sem consentimento: 409 antes de chamar o Fathom.
        blocked = client.post(
            f"/backoffice/sales-copilot/{session_id}/fathom-import",
            json={"recording_id": 1, "analyze_after_import": False},
        )
        assert_status(blocked, 409, "import sem consentimento")
        assert "consentimento" in blocked.json()["detail"].lower(), blocked.text
        print("import sem consentimento: 409 OK (nao chamou o Fathom)")

        configured = client.put(
            f"/backoffice/sales-copilot/{session_id}/meeting",
            json={"meeting_provider": "manual", "consent_granted": True},
        )
        assert_status(configured, 200, "registrar consentimento")

        after_consent = client.post(
            f"/backoffice/sales-copilot/{session_id}/fathom-import",
            json={"recording_id": 999999999, "analyze_after_import": False},
        )
        if has_key:
            # Gravação inexistente é erro do provedor, não sucesso silencioso.
            assert after_consent.status_code in (422, 502), after_consent.text
            print(f"import de gravacao inexistente: {after_consent.status_code} OK")
        else:
            assert_status(after_consent, 422, "import sem chave")
            assert "FATHOM_API_KEY" in after_consent.json()["detail"], after_consent.text
            print("import sem chave: 422 honesto OK")

        # Idempotência: dois segmentos com a mesma chave contam uma vez.
        with connect() as conn:
            for _ in range(2):
                copilot_repo.add_segment(
                    conn,
                    session_id,
                    None,
                    {
                        "idempotency_key": "fathom:smoke:0",
                        "source": "provider_webhook",
                        "participant_id": None,
                        "external_speaker_id": None,
                        "speaker_label": "Fulano",
                        "start_ms": 1000,
                        "end_ms": None,
                        "content": "segmento de smoke",
                        "confidence": None,
                        "is_final": True,
                    },
                )
            segments = copilot_repo.list_segments(conn, session_id, 5000)
        same_key = [item for item in segments if item["idempotency_key"] == "fathom:smoke:0"]
        assert len(same_key) == 1, f"idempotencia falhou: {len(same_key)} segmentos com a mesma chave"
        print("idempotencia por chave de segmento: OK")
    finally:
        with connect() as conn:
            conn.execute("delete from sales_copilot_sessions where id = %s", (session_id,))
    print("limpeza OK — smoke_fathom_import passou")


if __name__ == "__main__":
    main()
