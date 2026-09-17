"""Cache de traduções de proposta."""

from typing import Any
from uuid import UUID

from psycopg.rows import dict_row

COLUMNS = (
    "id, proposal_id, language, title, content_markdown, generation_mode, provider, model, "
    "input_tokens, output_tokens, cost_cents, created_by, created_at"
)


def get_cached(conn, proposal_id: UUID, language: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"select {COLUMNS} from proposal_translations where proposal_id = %s and language = %s",
            (proposal_id, language),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def save(conn, data: dict[str, Any]) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            insert into proposal_translations (
              proposal_id, language, title, content_markdown, generation_mode, provider, model,
              input_tokens, output_tokens, cost_cents, created_by
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (proposal_id, language) do update set
              title = excluded.title, content_markdown = excluded.content_markdown,
              generation_mode = excluded.generation_mode, provider = excluded.provider,
              model = excluded.model, input_tokens = excluded.input_tokens,
              output_tokens = excluded.output_tokens, cost_cents = excluded.cost_cents,
              created_by = excluded.created_by, created_at = now()
            returning {COLUMNS}
            """,
            (
                data["proposal_id"], data["language"], data["title"], data["content_markdown"],
                data["generation_mode"], data.get("provider"), data.get("model"),
                data.get("input_tokens"), data.get("output_tokens"), data.get("cost_cents"),
                data.get("created_by"),
            ),
        )
        return dict(cur.fetchone())


def invalidate(conn, proposal_id: UUID) -> None:
    """Editar o original invalida TODAS as traduções — tradução desatualizada
    lida como se fosse atual é pior que reprocessar."""
    conn.execute("delete from proposal_translations where proposal_id = %s", (proposal_id,))
