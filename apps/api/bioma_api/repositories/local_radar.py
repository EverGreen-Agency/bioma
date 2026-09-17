from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

SCAN_COLUMNS = "id, created_by, niche, city, query_text, status, source, error_message, prospect_count, created_at"

PROSPECT_COLUMNS = (
    "id, scan_id, place_id, name, address, phone, website, google_maps_url, rating, "
    "rating_count, business_status, place_types, presence_score, presence_gaps, changes, "
    "audit, audit_mode, outreach_message, review_status, reviewed_by, reviewed_at, lead_id, "
    "sent_at, created_at, updated_at"
)


def create_scan(conn, created_by: UUID, values: dict[str, Any]) -> dict[str, Any]:
    return conn.execute(
        f"""
        insert into local_radar_scans (created_by, niche, city, query_text, status, source, error_message, prospect_count)
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        returning {SCAN_COLUMNS}
        """,
        (
            created_by,
            values["niche"],
            values["city"],
            values["query_text"],
            values.get("status", "completed"),
            values.get("source", "places"),
            values.get("error_message"),
            values.get("prospect_count", 0),
        ),
    ).fetchone()


def list_scans(conn, limit: int = 50) -> list[dict[str, Any]]:
    return conn.execute(
        f"select {SCAN_COLUMNS} from local_radar_scans order by created_at desc limit %s",
        (limit,),
    ).fetchall()


def get_scan(conn, scan_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"select {SCAN_COLUMNS} from local_radar_scans where id = %s",
        (scan_id,),
    ).fetchone()


def insert_prospects(conn, scan_id: UUID, prospects: list[dict[str, Any]]) -> int:
    count = 0
    for prospect in prospects:
        if not prospect.get("place_id"):
            continue
        conn.execute(
            """
            insert into local_radar_prospects (
              scan_id, place_id, name, address, phone, website, google_maps_url,
              rating, rating_count, business_status, place_types, presence_score,
              presence_gaps, changes
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (scan_id, place_id) do nothing
            """,
            (
                scan_id,
                prospect["place_id"],
                prospect["name"],
                prospect.get("address"),
                prospect.get("phone"),
                prospect.get("website"),
                prospect.get("google_maps_url"),
                prospect.get("rating"),
                prospect.get("rating_count"),
                prospect.get("business_status"),
                prospect.get("place_types") or [],
                prospect.get("presence_score"),
                Jsonb(prospect.get("presence_gaps") or []),
                Jsonb(prospect.get("changes") or []),
            ),
        )
        count += 1
    conn.execute(
        "update local_radar_scans set prospect_count = (select count(*) from local_radar_prospects where scan_id = %s) where id = %s",
        (scan_id, scan_id),
    )
    return count


def list_prospects(conn, scan_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        f"""
        select {PROSPECT_COLUMNS} from local_radar_prospects
        where scan_id = %s
        order by presence_score asc nulls last, rating_count asc nulls last
        """,
        (scan_id,),
    ).fetchall()


def get_prospect(conn, prospect_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"select {PROSPECT_COLUMNS} from local_radar_prospects where id = %s",
        (prospect_id,),
    ).fetchone()


def update_prospect(conn, prospect_id: UUID, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {
        "audit", "audit_mode", "outreach_message", "review_status",
        "reviewed_by", "reviewed_at", "lead_id", "sent_at",
    }
    fields = {key: value for key, value in updates.items() if key in allowed}
    if not fields:
        return get_prospect(conn, prospect_id)
    assignments = ", ".join(f"{key} = %s" for key in fields)
    values = [Jsonb(value) if key == "audit" else value for key, value in fields.items()]
    return conn.execute(
        f"""
        update local_radar_prospects set {assignments}, updated_at = now()
        where id = %s
        returning {PROSPECT_COLUMNS}
        """,
        (*values, prospect_id),
    ).fetchone()


def previous_prospects_by_place(conn, place_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Snapshot mais recente de cada place_id em scans anteriores — base do diff
    de rescan ("criou site desde o último scan") e da deduplicação de leads."""
    if not place_ids:
        return {}
    rows = conn.execute(
        """
        select distinct on (place_id)
               place_id, website, phone, rating, rating_count, lead_id, review_status
        from local_radar_prospects
        where place_id = any(%s)
        order by place_id, created_at desc
        """,
        (place_ids,),
    ).fetchall()
    return {row["place_id"]: row for row in rows}


def latest_research_playbook(conn, niche: str) -> dict[str, Any] | None:
    """Pesquisa de mercado concluída mais recente cujo setor bate com o nicho
    (match frouxo nos dois sentidos). Retorna o playbook de prospecção, se houver."""
    row = conn.execute(
        """
        select id, sector, report
        from market_researches
        where status = 'completed' and report is not null
          and (sector ilike '%%' || %s || '%%' or %s ilike '%%' || sector || '%%')
        order by completed_at desc nulls last, created_at desc
        limit 1
        """,
        (niche, niche),
    ).fetchone()
    if not row:
        return None
    playbook = (row["report"] or {}).get("prospecting_playbook")
    if not playbook:
        return None
    return {"research_id": str(row["id"]), "sector": row["sector"], "playbook": playbook}


def eg_context(conn) -> dict[str, Any] | None:
    """Organização e workspace interno da EG: destino dos leads convertidos e
    dono da configuração de WhatsApp usada no outbound."""
    return conn.execute(
        """
        select o.id as organization_id, w.id as workspace_id
        from organizations o
        join workspaces w on w.subject_organization_id = o.id
        where o.slug = 'eg'
        limit 1
        """,
    ).fetchone()
