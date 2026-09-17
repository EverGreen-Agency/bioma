"""Smoke do mural de vitórias, contra o Postgres real.

O que decide se o mural presta:

- **detector é idempotente** — rodar de novo não transforma a mesma proposta
  ganha em duas vitórias. Sem isso o mural vira spam em um dia;
- **vitória automática carrega evidência** — qual tabela, qual id. Sem isso ela é
  indistinguível de vitória inventada, e o mural inteiro perde valor na primeira
  linha que alguém duvidar;
- **janela desde a última varredura** — a primeira execução não pode despejar a
  história inteira e enterrar o que aconteceu hoje;
- **detector quebrado não derruba os outros** — mural em branco por causa de um
  detector novo com bug seria pior que o bug;
- **vitória interna não vaza para o cliente** — o filtro é do backend;
- **exportação para o Fóton leva só o do CEO**, e fica na auditoria.
"""

from pathlib import Path
import atexit
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from bioma_api import win_detectors
from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-wins-client@bioma.example.com"
PASSWORD = "senha-dev-123"
SMOKE_MARK = "SMOKE-WINS"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def cleanup() -> None:
    with connect() as conn:
        conn.execute("delete from wins where title like %s or description like %s", (f"%{SMOKE_MARK}%",) * 2)
        conn.execute("delete from wins where rule_key = 'smoke_detector'")
        conn.execute("delete from win_detector_runs where rule_key in ('smoke_detector', 'smoke_broken')")


def main() -> None:
    workspace = create_smoke_workspace("WINS")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Wins Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    atexit.register(cleanup)
    workspace_id = str(workspace.workspace_id)

    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    assert_status(
        client_user.post("/wins", json={"title": f"{SMOKE_MARK} tentativa"}), 403, "cliente nao registra"
    )
    assert_status(client_user.post("/wins/detect"), 403, "cliente nao roda detectores")
    print("escopo EG-only para escrita: 403 OK")

    win_ids: list[str] = []
    original_detectors = dict(win_detectors.DETECTORS)
    try:
        # 1) Registro manual — para o que não está em tabela nenhuma.
        manual = admin.post(
            "/wins",
            json={
                "title": f"{SMOKE_MARK} conta aprovada na plataforma nova",
                "description": "Cadastro liberado depois de duas semanas de análise.",
                "category": "comercial",
                "is_ceo": True,
                "metric_value": "1",
                "metric_unit": "conta",
            },
        )
        assert_status(manual, 201, "registro manual")
        manual_win = manual.json()
        win_ids.append(manual_win["id"])
        assert manual_win["source"] == "manual" and manual_win["created_by"], manual_win
        assert manual_win["evidence"] == {}, "vitoria manual nao inventa evidencia"
        print("registro manual OK (sem evidencia fabricada)")

        # 2) Detector determinístico: idempotência e evidência.
        occurred = datetime.now(timezone.utc) - timedelta(days=1)

        def smoke_detector(_conn, since):
            if occurred < since:
                return []
            return [
                {
                    "rule_key": "smoke_detector",
                    "dedupe_key": "smoke_detector:linha-1",
                    "title": f"{SMOKE_MARK} detectada automaticamente",
                    "description": None,
                    "category": "operacao",
                    "source": "automatic",
                    "occurred_at": occurred,
                    "evidence": {"table": "tabela_ficticia", "id": "linha-1", "status": "ok"},
                }
            ]

        def broken_detector(_conn, _since):
            raise RuntimeError("consulta invalida no detector novo")

        win_detectors.DETECTORS.clear()
        win_detectors.DETECTORS.update({"smoke_detector": smoke_detector, "smoke_broken": broken_detector})

        first = admin.post("/wins/detect")
        assert_status(first, 200, "primeira varredura")
        result = first.json()
        assert result["created"] == 1, result
        assert result["by_rule"]["smoke_detector"] == 1, result
        # Detector quebrado não derruba o resto.
        assert "smoke_broken" in result["errors"], result["errors"]
        assert "consulta invalida" in result["errors"]["smoke_broken"], result["errors"]
        print(f"varredura criou 1 vitoria; detector quebrado isolado no resultado OK")

        detected = next(
            row for row in admin.get("/wins").json() if row["rule_key"] == "smoke_detector"
        )
        win_ids.append(detected["id"])
        assert detected["source"] == "automatic", detected
        assert detected["evidence"]["table"] == "tabela_ficticia", (
            "vitoria automatica sem evidencia e indistinguivel de inventada"
        )
        print("vitoria automatica carrega a evidencia (tabela + id) OK")

        # 3) Rodar de novo NÃO duplica.
        second = admin.post("/wins/detect")
        assert_status(second, 200, "segunda varredura")
        assert second.json()["created"] == 0, (
            f"detector duplicou a mesma vitoria: {second.json()}"
        )
        total = len([row for row in admin.get("/wins").json() if row["rule_key"] == "smoke_detector"])
        assert total == 1, f"esperava 1 vitoria do detector, achei {total}"
        print("segunda varredura: 0 criadas, mural sem duplicata OK")

        # 4) A janela avança: o que é anterior à última varredura não volta.
        with connect() as conn:
            last = conn.execute(
                "select last_scanned_at, total_found from win_detector_runs where rule_key = 'smoke_detector'"
            ).fetchone()
        assert last["total_found"] == 1, last
        assert last["last_scanned_at"] > occurred, "a janela precisa avancar apos a varredura"
        print("janela da varredura avancou — historico antigo nao volta OK")

        # 5) Reação alterna e a contagem vem de quem reagiu.
        reacted = admin.post(f"/wins/{manual_win['id']}/react", json={"emoji": "🎉"})
        assert_status(reacted, 200, "reagir")
        assert len(reacted.json()["reactions"]["🎉"]) == 1, reacted.json()["reactions"]
        again = admin.post(f"/wins/{manual_win['id']}/react", json={"emoji": "🎉"})
        assert "🎉" not in again.json()["reactions"], (
            f"reagir de novo tem que desfazer: {again.json()['reactions']}"
        )
        print("reacao alterna e some quando zera OK")

        # 6) Vitória interna NÃO vaza para o cliente; liberada, aparece.
        interna = admin.post(
            "/wins",
            json={"title": f"{SMOKE_MARK} refatoracao interna", "workspace_id": workspace_id},
        )
        assert_status(interna, 201, "vitoria interna")
        win_ids.append(interna.json()["id"])
        client_view = client_user.get(f"/wins?workspace_id={workspace_id}")
        assert_status(client_view, 200, "cliente lista")
        assert not any(row["id"] == interna.json()["id"] for row in client_view.json()), (
            "vitoria interna vazou para o cliente"
        )

        assert_status(
            admin.patch(f"/wins/{interna.json()['id']}", json={"visibility": "client"}), 200, "liberar"
        )
        client_view = client_user.get(f"/wins?workspace_id={workspace_id}").json()
        assert any(row["id"] == interna.json()["id"] for row in client_view), (
            "vitoria liberada deveria aparecer para o cliente"
        )
        assert all(row["visibility"] == "client" for row in client_view), (
            f"cliente recebeu vitoria nao liberada no payload: {client_view}"
        )
        print("visibilidade: interna nao vaza, liberada aparece OK")

        # 7) Exportação para o Fóton leva só o do CEO.
        export = admin.get("/wins/export/foton?days=30")
        assert_status(export, 200, "exportar")
        package = export.json()
        assert package["scope"] == "ceo_wins" and package["purpose"], package
        titles = {item["title"] for item in package["wins"]}
        assert f"{SMOKE_MARK} conta aprovada na plataforma nova" in titles, titles
        assert f"{SMOKE_MARK} refatoracao interna" not in titles, (
            "exportacao do CEO nao pode levar vitoria que nao e do CEO"
        )
        assert all("evidence" in item for item in package["wins"]), "vitoria exportada sem origem vira anedota"
        with connect() as conn:
            audit = conn.execute(
                "select count(*) as n from audit_logs where event_type = 'wins.exported_to_foton'"
            ).fetchone()["n"]
        assert audit >= 1, "exportacao precisa ficar na trilha de auditoria"
        print(f"exportacao para o Foton: {len(package['wins'])} vitoria(s) do CEO, auditada OK")

        # 8) Agregado.
        overview = admin.get("/wins/overview?days=30")
        assert_status(overview, 200, "agregado")
        summary = overview.json()
        assert summary["manual"] >= 2 and summary["automatic"] >= 1, summary
        assert summary["ceo"] >= 1, summary
        print(
            f"agregado: {summary['total']} vitoria(s), {summary['automatic']} automatica(s), "
            f"{summary['ceo']} do CEO OK"
        )

        # 9) Os detectores reais compilam e rodam contra o banco de verdade.
        win_detectors.DETECTORS.clear()
        win_detectors.DETECTORS.update(original_detectors)
        real = admin.post("/wins/detect")
        assert_status(real, 200, "detectores reais")
        assert not real.json()["errors"], f"detector real com erro de SQL: {real.json()['errors']}"
        print(f"os {len(original_detectors)} detectores reais rodaram sem erro de consulta OK")
    finally:
        win_detectors.DETECTORS.clear()
        win_detectors.DETECTORS.update(original_detectors)
        with connect() as conn:
            for win_id in win_ids:
                conn.execute("delete from wins where id = %s", (win_id,))
            # O passo 9 roda os detectores REAIS de propósito — e o cliente
            # deste smoke ainda estava `active` naquele momento, então
            # `cliente_ativado` criou uma vitória de verdade sobre ele. Ela não
            # tem `workspace_id` (o detector não preenche), então o cascade de
            # apagar o workspace não a leva junto: sem esta limpeza, sobra uma
            # vitória "Cliente ativo na carteira: Smoke WINS xxxx" para sempre
            # no mural — foi assim que 5 delas foram parar lá durante o
            # desenvolvimento deste smoke.
            conn.execute(
                "delete from wins where evidence->>'id' = %s", (str(workspace.client_id),)
            )
        cleanup()
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_wins passou")


if __name__ == "__main__":
    main()
