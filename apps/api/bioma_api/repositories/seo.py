from uuid import UUID

from psycopg.types.json import Jsonb


COLUMNS = """id, workspace_id, source, source_endpoint, source_task_id, target,
location_code, language_code, has_data, organic, paid, cost_usd, measured_at, created_at"""


def latest_snapshot(conn, workspace_id: UUID):
    return conn.execute(
        f"select {COLUMNS} from seo_snapshots where workspace_id = %s order by created_at desc limit 1",
        (workspace_id,),
    ).fetchone()


def snapshot_by_hash(conn, workspace_id: UUID, response_sha256: str):
    return conn.execute(
        f"select {COLUMNS} from seo_snapshots where workspace_id = %s and response_sha256 = %s",
        (workspace_id, response_sha256),
    ).fetchone()


def insert_snapshot(conn, workspace_id: UUID, collected_by: UUID, snapshot: dict, response_sha256: str):
    return conn.execute(
        f"""
        insert into seo_snapshots (
          workspace_id, source, source_endpoint, source_task_id, target,
          location_code, language_code, has_data, organic, paid, raw_response,
          response_sha256, cost_usd, measured_at, collected_by
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (workspace_id, response_sha256) do nothing
        returning {COLUMNS}
        """,
        (
            workspace_id, snapshot["source"], snapshot["source_endpoint"], snapshot.get("source_task_id"),
            snapshot["target"], snapshot["location_code"], snapshot["language_code"], snapshot["has_data"],
            Jsonb(snapshot["organic"]), Jsonb(snapshot["paid"]), Jsonb(snapshot["raw_response"]),
            response_sha256, snapshot.get("cost_usd"), snapshot["measured_at"], collected_by,
        ),
    ).fetchone()
