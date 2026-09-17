"""Smoke do estudo de plataformas (build vs. buy), contra o Postgres real.

Valida:
- só EG;
- URL é normalizada e deduplicada — `ramp.com`, `https://ramp.com` e
  `https://ramp.com/` são a mesma empresa, não três linhas na lista;
- captura em lote não dispara pesquisa (capturar é de graça, analisar custa);
- pesquisa grava fontes, tokens e custo, e calcula a prioridade de teste;
- falha de pesquisa vira `failed` com o motivo escrito — não exceção, porque
  "o site exige JavaScript" é informação sobre a plataforma;
- veredito é humano e fica assinado;
- o agregado conta as plataformas de sobreposição alta, que é o número que pesa
  na decisão de continuar construindo.

O analisador é injetado: o que se testa aqui é a autoridade da API, não a
leitura do modelo. A busca real de páginas é exercitada em `fetch_pages`, que
roda contra sites de verdade.
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
from bioma_api.services import platform_studies as service
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-platform-client@bioma.example.com"
PASSWORD = "senha-dev-123"

# Domínio reservado para exemplo (RFC 2606) — nunca vai virar empresa de verdade
# e colidir com a lista real do Eduardo.
TEST_URLS = ["smoke-alpha.example.com", "smoke-beta.example.com", "smoke-gamma.example.com"]


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def fake_analyze(overlap=85, threat="critica", worth_test=True, model="gpt-4o-mini"):
    def _analyze(request):
        return {
            "output": {
                "name": "Alpha Suite",
                "category": "Gestão de projetos",
                "one_liner": "Board de tarefas com automação para agências.",
                "pricing_summary": "US$ 12/usuário/mês no plano Pro.",
                "what_it_does": ["Board kanban", "Automação de status"],
                "who_its_for": "Agências pequenas",
                "has_that_bioma_lacks": ["App mobile nativo"],
                "bioma_has_that_it_lacks": ["Hub do cliente com aprovação de entrega"],
                "overlap_score": overlap,
                "threat_level": threat,
                "recommended_verdict": "repensar",
                "verdict_reason": "Cobre a gestão de tarefas melhor que o Bioma hoje.",
                "worth_hands_on_test": worth_test,
                "open_questions": ["Aguenta multi-cliente com permissões separadas?"],
            },
            "sources": [f"https://{request['url'].split('//')[-1]}", f"{request['url']}/pricing"],
            "preview_image": "https://smoke-alpha.example.com/og.png",
            "generation_mode": "live",
            "provider": "openai",
            "model": model,
            "usage": {"input_tokens": 8000, "output_tokens": 700},
        }

    return _analyze


def cleanup() -> None:
    with connect() as conn:
        conn.execute(
            "delete from platform_studies where url like %s", ("https://smoke-%.example.com",)
        )


def main() -> None:
    workspace = create_smoke_workspace("PLATFORM")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Platform Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    atexit.register(cleanup)

    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    assert_status(client_user.get("/platform-studies"), 403, "cliente nao lista plataformas")
    assert_status(
        client_user.post("/platform-studies", json={"url": "x.com"}), 403, "cliente nao adiciona"
    )
    print("escopo EG-only: 403 para client_user OK")

    original_analyze = service.platform_study_analyze_safe
    try:
        # 1) Captura em lote, com as três grafias da MESMA URL no meio.
        bulk = admin.post(
            "/platform-studies/bulk",
            json={
                "urls": TEST_URLS + ["https://smoke-alpha.example.com/", "SMOKE-ALPHA.EXAMPLE.COM"],
                "targets": ["bioma", "foton"],
            },
        )
        assert_status(bulk, 201, "captura em lote")
        with connect() as conn:
            count = conn.execute(
                "select count(*) as n from platform_studies where url like %s", ("https://smoke-%.example.com",)
            ).fetchone()["n"]
        assert count == 3, f"esperava 3 plataformas apos dedupe de grafia, veio {count}"
        print(f"captura em lote: 5 grafias -> {count} plataformas (dedupe por URL) OK")

        listing = admin.get("/platform-studies?research_status=pending").json()
        mine = [row for row in listing if row["url"].startswith("https://smoke-")]
        assert len(mine) == 3, mine
        assert all(row["research_status"] == "pending" for row in mine), (
            "captura nao pode disparar pesquisa — analisar 78 plataformas de uma vez custaria caro"
        )
        assert all(row["name"] for row in mine), "nome derivado do dominio nao pode ficar vazio"
        alpha = next(row for row in mine if "alpha" in row["url"])
        assert alpha["name"] == "Smoke Alpha", alpha["name"]
        print("nada foi pesquisado na captura, e todas tem nome legivel OK")

        # 2) Pesquisa: grava fonte, token, custo e prioridade.
        service.platform_study_analyze_safe = fake_analyze()
        researched = admin.post(f"/platform-studies/{alpha['id']}/research")
        assert_status(researched, 200, "pesquisar")
        row = researched.json()
        assert row["research_status"] == "researched", row
        assert row["name"] == "Alpha Suite", "nome real da pesquisa deveria substituir o derivado"
        assert len(row["sources"]) == 2, "analise sem fonte e opiniao sobre um dominio"
        assert row["input_tokens"] == 8000 and row["output_tokens"] == 700, row
        assert row["cost_cents"] == cost_cents("gpt-4o-mini", 8000, 700), row["cost_cents"]
        assert row["overlap_score"] == 85 and row["threat_level"] == "critica", row
        # overlap 85 // 2 = 42, + 50 (critica) + 15 (vale testar) = 100 (teto)
        assert row["test_priority"] == 100, row["test_priority"]
        assert row["findings"]["bioma_has_that_it_lacks"], row["findings"]
        print(
            f"pesquisa OK — {len(row['sources'])} fonte(s), {row['input_tokens']}+{row['output_tokens']} tokens, "
            f"custo {row['cost_cents']}c, prioridade {row['test_priority']}"
        )

        # 3) Modelo sem preço na tabela: custo fica em branco, nunca estimado.
        service.platform_study_analyze_safe = fake_analyze(model="modelo-que-nao-existe")
        beta = next(row for row in mine if "beta" in row["url"])
        no_price = admin.post(f"/platform-studies/{beta['id']}/research").json()
        assert no_price["input_tokens"] == 8000, no_price
        assert no_price["cost_cents"] is None, (
            f"modelo sem preco tem que ficar sem custo, nao estimado: {no_price['cost_cents']}"
        )
        print("modelo sem preco na tabela: token registrado, custo em branco OK")

        # 4) Falha vira `failed` com motivo — não exceção.
        def broken(_request):
            raise RuntimeError("Nenhuma página pública legível: site exige JavaScript.")

        service.platform_study_analyze_safe = broken
        gamma = next(row for row in mine if "gamma" in row["url"])
        failed = admin.post(f"/platform-studies/{gamma['id']}/research")
        assert_status(failed, 200, "pesquisa que falha continua 200")
        failed_row = failed.json()
        assert failed_row["research_status"] == "failed", failed_row
        assert "JavaScript" in (failed_row["research_error"] or ""), failed_row
        print("falha de pesquisa: registrada com o motivo, sem derrubar a chamada OK")

        # 5) Veredito é humano e fica assinado.
        decided = admin.post(
            f"/platform-studies/{alpha['id']}/verdict",
            json={"verdict": "repensar", "verdict_note": "Testar antes de investir mais no board."},
        )
        assert_status(decided, 200, "veredito")
        decision = decided.json()
        assert decision["verdict"] == "repensar" and decision["decided_by"], decision
        assert decision["decided_at"], "decisao sem data nao serve para revisitar depois"
        print("veredito humano registrado com autor e data OK")

        # 6) Agregado conta o que pesa na decisão de continuar.
        overview = admin.get("/platform-studies/overview")
        assert_status(overview, 200, "agregado")
        summary = overview.json()
        assert summary["high_threat"] >= 2, summary
        assert summary["rethink_bioma"] >= 1, summary
        assert any(item["name"] == "Alpha Suite" for item in summary["critical_overlap"]), summary
        print(
            f"agregado: {summary['total']} na lista, {summary['high_threat']} de sobreposicao alta, "
            f"{summary['rethink_bioma']} marcada(s) 'repensar' OK"
        )

        # 7) Filtro por veredito.
        filtered = admin.get("/platform-studies?verdict=repensar").json()
        assert any(row["id"] == alpha["id"] for row in filtered), filtered
        print("filtro por veredito OK")

        # 8) Remover.
        assert_status(admin.delete(f"/platform-studies/{beta['id']}"), 200, "remover")
        assert_status(admin.delete(f"/platform-studies/{beta['id']}"), 404, "remover duas vezes")
        print("remover e 404 na segunda vez OK")
    finally:
        service.platform_study_analyze_safe = original_analyze
        cleanup()
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_platform_studies passou")


if __name__ == "__main__":
    main()
