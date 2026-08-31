"""Persistência dos estudos de plataforma (build vs. buy)."""

from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

COLUMNS = """
  id, url, name, targets, added_note,
  research_status, research_error, category, one_liner, pricing_summary,
  findings, sources, preview_image_url,
  overlap_score, threat_level, test_priority,
  verdict, verdict_note, decided_by, decided_at,
  generation_mode, provider, model, input_tokens, output_tokens, cost_cents,
  researched_at, created_by, created_at, updated_at
"""


def add(conn, url: str, name: str, targets: list[str], note: str | None, created_by: UUID) -> dict[str, Any]:
    """Idempotente por URL: a mesma plataforma colada duas vezes não vira duas
    linhas. Colar de novo atualiza as frentes e a nota — que é o que a pessoa
    quis dizer ao colar de novo."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            insert into platform_studies (url, name, targets, added_note, created_by)
            values (%s, %s, %s, %s, %s)
            on conflict (url) do update set
              targets = excluded.targets,
              added_note = coalesce(excluded.added_note, platform_studies.added_note),
              updated_at = now()
            returning {COLUMNS}
            """,
            (url, name, Jsonb(targets), note, created_by),
        )
        return dict(cur.fetchone())


def get(conn, study_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"select {COLUMNS} from platform_studies where id = %s", (study_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def list_all(
    conn, research_status: str | None = None, verdict: str | None = None, target: str | None = None
) -> list[dict[str, Any]]:
    """Ordenado pela fila de teste: quem pode responder "pare de construir" primeiro."""
    query = f"select {COLUMNS} from platform_studies"
    clauses: list[str] = []
    params: list[Any] = []
    if research_status:
        clauses.append("research_status = %s")
        params.append(research_status)
    if verdict:
        clauses.append("verdict = %s")
        params.append(verdict)
    if target:
        clauses.append("targets ? %s")
        params.append(target)
    if clauses:
        query += " where " + " and ".join(clauses)
    query += " order by test_priority desc nulls last, overlap_score desc nulls last, name"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def mark_researching(conn, study_id: UUID) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "update platform_studies set research_status = 'researching', research_error = null, updated_at = now() where id = %s",
            (study_id,),
        )


def save_research(conn, study_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            update platform_studies set
              research_status = 'researched', research_error = null,
              name = %s, category = %s, one_liner = %s, pricing_summary = %s,
              findings = %s, sources = %s, preview_image_url = coalesce(%s, preview_image_url),
              overlap_score = %s, threat_level = %s, test_priority = %s,
              generation_mode = %s, provider = %s, model = %s,
              input_tokens = %s, output_tokens = %s, cost_cents = %s,
              researched_at = now(), updated_at = now()
            where id = %s
            returning {COLUMNS}
            """,
            (
                data["name"], data["category"], data["one_liner"], data["pricing_summary"],
                Jsonb(data["findings"]), Jsonb(data["sources"]), data.get("preview_image_url"),
                data["overlap_score"], data["threat_level"], data["test_priority"],
                data.get("generation_mode"), data.get("provider"), data.get("model"),
                data.get("input_tokens"), data.get("output_tokens"), data.get("cost_cents"),
                study_id,
            ),
        )
        return dict(cur.fetchone())


def mark_failed(conn, study_id: UUID, error: str) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            update platform_studies
            set research_status = 'failed', research_error = %s, updated_at = now()
            where id = %s returning {COLUMNS}
            """,
            (error[:2000], study_id),
        )
        return dict(cur.fetchone())


def set_verdict(conn, study_id: UUID, verdict: str, note: str | None, decided_by: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            update platform_studies
            set verdict = %s, verdict_note = %s, decided_by = %s, decided_at = now(), updated_at = now()
            where id = %s returning {COLUMNS}
            """,
            (verdict, note, decided_by, study_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete(conn, study_id: UUID) -> bool:
    with conn.cursor() as cur:
        cur.execute("delete from platform_studies where id = %s", (study_id,))
        return cur.rowcount > 0


def overview(conn) -> dict[str, Any]:
    """O agregado que responde a pergunta grande.

    `critical_overlap` são as plataformas que fazem melhor o que o Bioma se
    proponha a fazer. É esse número — e a lista por trás dele — que dá a resposta
    honesta para "continuo construindo?", em vez de uma sensação.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
              count(*) as total,
              count(*) filter (where research_status = 'pending') as pending,
              count(*) filter (where research_status = 'researched') as researched,
              count(*) filter (where research_status = 'failed') as failed,
              count(*) filter (where verdict is not null) as decided,
              count(*) filter (where threat_level in ('alta', 'critica')) as high_threat,
              count(*) filter (where verdict = 'repensar') as rethink_bioma,
              coalesce(sum(cost_cents), 0) as cost_cents,
              coalesce(round(avg(overlap_score) filter (where overlap_score is not null)), 0) as avg_overlap
            from platform_studies
            """
        )
        summary = dict(cur.fetchone())
        cur.execute(
            """
            select id, name, url, one_liner, overlap_score, threat_level, verdict
            from platform_studies
            where threat_level in ('alta', 'critica')
            order by overlap_score desc nulls last
            limit 10
            """
        )
        summary["critical_overlap"] = [dict(row) for row in cur.fetchall()]
    return summary
