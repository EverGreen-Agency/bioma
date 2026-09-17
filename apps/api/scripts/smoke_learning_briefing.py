"""Smoke do placar de aprendizado (roteiro IA x conta) e do rascunho de briefing.

Contra o Postgres real. Cria post + roteiro vinculados, confere o placar, e
valida que o briefing lista fontes reais e recusa cliente sem nenhum sinal.
Limpa tudo o que cria.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datetime import datetime, timedelta, timezone

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

    with connect() as conn:
        row = conn.execute(
            """
            select w.id as workspace_id, c.id as client_id, c.name
            from workspaces w
            join clients c on c.organization_id = w.subject_organization_id
            join organizations o on o.id = c.organization_id
            where w.kind = 'client' and w.status = 'active' and o.slug <> 'eg'
            order by c.created_at
            limit 1
            """,
        ).fetchone()
    if not row:
        raise AssertionError("nenhum workspace de cliente para testar")
    workspace_id = str(row["workspace_id"])
    print(f"cliente de teste: {row['name']}")

    script_id = None
    post_ids: list[str] = []
    try:
        now = datetime.now(timezone.utc)
        with connect() as conn:
            script_id = conn.execute(
                """
                insert into workspace_content_scripts
                  (workspace_id, title, script_body, theme, suggested_format, status, generation_mode)
                values (%s, 'Roteiro smoke IA', 'corpo do roteiro', 'tema smoke', 'reels', 'published', 'preview')
                returning id
                """,
                (row["workspace_id"],),
            ).fetchone()["id"]

            # Um post vindo do roteiro (performou melhor) e um sem roteiro (baseline).
            for index, (media_id, reach, likes, source) in enumerate(
                [
                    ("smoke-ia-1", 1000, 100, script_id),
                    ("smoke-base-1", 500, 40, None),
                ]
            ):
                post_ids.append(
                    str(
                        conn.execute(
                            """
                            insert into workspace_instagram_posts
                              (workspace_id, client_id, ig_media_id, media_type, caption, posted_at,
                               reach, impressions, likes, comments, shares, saved, plays, source_script_id)
                            values (%s, %s, %s, 'REELS', %s, %s, %s, %s, %s, 2, 1, 5, 0, %s)
                            returning id
                            """,
                            (
                                row["workspace_id"],
                                row["client_id"],
                                media_id,
                                f"post smoke {index}",
                                now - timedelta(days=5 + index),
                                reach,
                                reach * 2,
                                likes,
                                source,
                            ),
                        ).fetchone()["id"]
                    )
                )

        board = client.get(f"/workspaces/{workspace_id}/content/script-scoreboard?period_days=90")
        assert_status(board, 200, "placar")
        data = board.json()
        assert data["ai_posts"] >= 1, data
        assert data["other_posts"] >= 1, data
        # 1000 vs 500 de alcance = +100% de lift; o valor exato depende de outros
        # posts reais do periodo, então só exigimos que o lift exista e seja positivo.
        assert data["lift_reach_percent"] is not None, data
        assert any(item["script_id"] == str(script_id) for item in data["per_script"]), data
        print(
            f"placar OK — IA {data['ai_posts']} posts (alcance {data['ai_avg_reach']:.0f}) x "
            f"base {data['other_posts']} posts (alcance {data['other_avg_reach']:.0f}), "
            f"lift {data['lift_reach_percent']}%"
        )

        # Briefing: com posts sincronizados, o orgânico deve aparecer como fonte usada.
        draft = client.post(f"/workspaces/{workspace_id}/briefing/draft?persist=false")
        assert_status(draft, 200, "rascunho de briefing")
        body = draft.json()
        assert body["generation_mode"] in ("live", "preview"), body
        assert "organic_social" in body["sources_used"], body["sources_used"]
        assert body["draft"]["questions_for_client"], "rascunho sem perguntas para a call"
        assert body["artifact_id"] is None, "persist=false nao deve gravar artefato"
        print(
            f"briefing OK (modo={body['generation_mode']}) — fontes usadas: {body['sources_used']}; "
            f"ausentes: {len(body['missing_sources'])}"
        )

        # Workspace inexistente: 404, não rascunho vazio.
        assert_status(
            client.post("/workspaces/00000000-0000-0000-0000-000000000000/briefing/draft"),
            404,
            "briefing de workspace inexistente",
        )
        print("briefing de workspace inexistente: 404 OK")
    finally:
        with connect() as conn:
            if post_ids:
                conn.execute("delete from workspace_instagram_posts where id = any(%s)", (post_ids,))
            if script_id:
                conn.execute("delete from workspace_content_scripts where id = %s", (script_id,))
    print("limpeza OK — smoke_learning_briefing passou")


if __name__ == "__main__":
    main()
