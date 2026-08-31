"""Smoke da tradução em cache de propostas, contra o Postgres real.

Desenho (decisão do Eduardo, 2026-08-04): um artefato, um idioma canônico,
traduções em cache. O link público nunca muda de idioma — a tradução é só
para a equipe interna ler algo que nasceu no idioma do lead.

Valida:
- só EG;
- primeira chamada chama o tradutor; a segunda, no MESMO idioma, lê do cache
  sem chamar de novo — é o que faz "custo zero da segunda vez" ser verdade;
- editar a proposta invalida o cache: a próxima leitura traduz de novo;
- custo é calculado normalmente aqui (ao contrário do copiloto roteado por
  assinatura) — tradução sempre roda por chave de API.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.model_pricing import cost_cents
from bioma_api.repositories import proposals as proposals_repo
from bioma_api.services import proposals as proposals_service
from smoke_support import upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-translate-client@bioma.example.com"
PASSWORD = "senha-dev-123"
TEST_URL = "https://www.99freelas.com.br/projeto-teste-traducao"
TEST_CLIENT = "Projeto Teste: Traducao"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def cleanup() -> None:
    with connect() as conn:
        conn.execute("delete from commercial_proposals where client_name = %s", (TEST_CLIENT,))
        conn.execute("delete from opportunity_radar where url = %s", (TEST_URL,))
        conn.execute("delete from users where lower(email) = %s", (CLIENT_EMAIL,))


def main() -> None:
    atexit.register(cleanup)
    upsert_smoke_user(CLIENT_EMAIL, "Translate Client Smoke", PASSWORD)

    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    with connect() as conn:
        opp = proposals_repo.create_opportunity(
            conn,
            {
                "source_platform": "99freelas",
                "title": "Projeto Teste Traducao",
                "url": TEST_URL,
                "description": "Teste de traducao.",
                "status": "qualified",
            },
        )
        proposal = proposals_repo.create_proposal(
            conn,
            {
                "opportunity_id": str(opp["id"]),
                "client_name": TEST_CLIENT,
                "title": "Proposta de teste",
                "executive_summary": "Vamos acelerar sua aquisicao de leads.",
                "scope_offer": "Definicao de proposta de valor.",
                "pricing_cents": 500000,
                "delivery_days": 10,
                "status": "draft",
            },
        )
    proposal_id = proposal["id"]

    assert_status(
        client_user.post(f"/backoffice/proposals/{proposal_id}/translate", json={"language": "en-US"}),
        403,
        "cliente nao traduz",
    )
    print("escopo EG-only: 403 para client_user OK")

    call_count = {"n": 0}
    original_translate = proposals_service.translate_proposal_safe

    def fake_translate(payload):
        call_count["n"] += 1
        return {
            "output": {
                "title": f"[EN] {payload['title']}",
                "content_markdown": f"[EN] {payload['content_markdown']}",
            },
            "generation_mode": "live",
            "provider": "openai",
            "model": "gpt-4o-mini",  # tem preço na tabela — tradução DEVE custar de verdade.
            "usage": {"input_tokens": 400, "output_tokens": 350},
        }

    proposals_service.translate_proposal_safe = fake_translate
    try:
        first = admin.post(f"/backoffice/proposals/{proposal_id}/translate", json={"language": "en-US"})
        assert_status(first, 200, "primeira traducao")
        body = first.json()
        assert body["title"].startswith("[EN]"), body
        assert body["generation_mode"] == "live" and body["provider"] == "openai", body
        expected_cost = cost_cents("gpt-4o-mini", 400, 350)
        assert body["cost_cents"] == expected_cost, (
            f"traducao roda por chave de API — TEM que ter custo, ao contrario do copiloto roteado: {body}"
        )
        assert call_count["n"] == 1, call_count
        print(f"primeira traducao: chamou o tradutor, custo {body['cost_cents']} centavos OK")

        second = admin.post(f"/backoffice/proposals/{proposal_id}/translate", json={"language": "en-US"})
        assert_status(second, 200, "segunda traducao (cache)")
        assert call_count["n"] == 1, (
            f"segunda chamada no MESMO idioma nao pode chamar o tradutor de novo — cache quebrado: {call_count}"
        )
        assert second.json()["id"] == body["id"], "cache deveria devolver a MESMA linha"
        print("segunda chamada leu do cache — tradutor nao foi chamado de novo OK")

        edited = admin.patch(f"/backoffice/proposals/{proposal_id}", json={"executive_summary": "Texto mudou."})
        assert_status(edited, 200, "editar proposta")

        third = admin.post(f"/backoffice/proposals/{proposal_id}/translate", json={"language": "en-US"})
        assert_status(third, 200, "terceira traducao (pos-edicao)")
        assert call_count["n"] == 2, (
            f"editar o original tem que invalidar o cache — tradutor deveria ter sido chamado de novo: {call_count}"
        )
        print("editar a proposta invalidou o cache — tradutor chamado de novo OK")

        with connect() as conn:
            remaining = conn.execute(
                "select count(*) as n from proposal_translations where proposal_id = %s", (proposal_id,)
            ).fetchone()["n"]
        assert remaining == 1, f"so devia sobrar 1 traducao (en-US) apos a invalidacao+retraducao: {remaining}"
        print("cache tem exatamente 1 linha por idioma, nao acumula versao velha OK")

        # A tela de edição de verdade não passa por `services/proposals.py`
        # (PATCH acima) — passa por `proposal_lifecycle.update_content`
        # (PUT .../content). São dois módulos de serviço diferentes para a
        # MESMA tabela; sem invalidar nos dois, editar pela tela deixaria a
        # tradução em cache mentindo.
        edited_via_lifecycle = admin.put(
            f"/backoffice/proposals/{proposal_id}/content",
            json={"content_markdown": "## Proposta\n\nConteudo editado pela tela de verdade, com bastante texto.", "claims": []},
        )
        assert_status(edited_via_lifecycle, 200, "editar conteudo via lifecycle")
        fourth = admin.post(f"/backoffice/proposals/{proposal_id}/translate", json={"language": "en-US"})
        assert_status(fourth, 200, "quarta traducao (pos-edicao via lifecycle)")
        assert call_count["n"] == 3, (
            f"editar pelo caminho REAL da tela (proposal_lifecycle) tambem tem que invalidar: {call_count}"
        )
        print("editar pelo caminho da tela (proposal_lifecycle) tambem invalida o cache OK")
    finally:
        proposals_service.translate_proposal_safe = original_translate
        cleanup()
    print("limpeza OK — smoke_proposal_translation passou")


if __name__ == "__main__":
    main()
