from typing import Any
from uuid import UUID


PROFILE_COLUMNS = (
    "sector, primary_offer, initial_objective, contact_email, contact_phone, website, "
    "business_address, business_details, target_audience, competitors, marketing_objectives, "
    "marketing_history, challenges_opportunities, resources_budget, tone_of_voice, "
    "preferences_restrictions, updated_at"
)


def get_profile(conn, workspace_id: UUID):
    return conn.execute(
        f"select {PROFILE_COLUMNS} from workspace_client_profiles where workspace_id = %s",
        (workspace_id,),
    ).fetchone()


def get_profile_for_organization(conn, organization_id: UUID):
    return conn.execute(
        f"""
        select {PROFILE_COLUMNS}
        from workspace_client_profiles profile
        join workspaces workspace on workspace.id = profile.workspace_id
        where workspace.subject_organization_id = %s
          and workspace.kind = 'client'
          and workspace.status = 'active'
        order by profile.updated_at desc
        limit 1
        """,
        (organization_id,),
    ).fetchone()


def upsert_profile(conn, workspace_id: UUID, user_id: UUID, payload: dict[str, Any]):
    columns = [key for key in payload]
    values = [payload[key] for key in columns]
    assignments = ", ".join(f"{column} = excluded.{column}" for column in columns)
    return conn.execute(
        f"""
        insert into workspace_client_profiles (
          workspace_id, {", ".join(columns)}, created_by, updated_by
        ) values (%s, {", ".join("%s" for _ in columns)}, %s, %s)
        on conflict (workspace_id) do update set
          {assignments}, updated_by = excluded.updated_by, updated_at = now()
        returning {PROFILE_COLUMNS}
        """,
        (workspace_id, *values, user_id, user_id),
    ).fetchone()
