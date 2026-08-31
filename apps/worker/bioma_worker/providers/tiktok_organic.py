from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from psycopg.types.json import Jsonb

from bioma_worker.crypto import decrypt_secret, encrypt_secret
from bioma_worker.storage import resolve_workspace_id, upsert_rows

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"
VIDEO_FIELDS = "id,title,create_time,like_count,comment_count,share_count,view_count"


def sync(
    conn,
    client: httpx.Client,
    settings,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    if not settings.secret_encryption_key:
        raise RuntimeError("SECRET_ENCRYPTION_KEY não configurado no worker — necessário pra decifrar o token do TikTok.")

    access_token = _access_token(conn, connection, settings)
    items = _list_videos(client, access_token, date_from)
    workspace_id = resolve_workspace_id(conn, client_id)

    rows = [_row(workspace_id, client_id, item) for item in items]
    return upsert_rows(
        conn,
        "workspace_tiktok_organic_videos",
        ("workspace_id", "client_id", "video_id", "title", "posted_at", "view_count", "like_count", "comment_count", "share_count"),
        ("workspace_id", "video_id"),
        rows,
    )


def _access_token(conn, connection: dict[str, Any], settings) -> str:
    metadata = connection.get("metadata") or {}
    encrypted_access = metadata.get("oauth_access_token")
    if not encrypted_access:
        raise RuntimeError("Conexão TikTok sem token OAuth salvo — refaça a autorização em Integrações.")

    expires_at_raw = metadata.get("oauth_expires_at")
    needs_refresh = False
    if expires_at_raw:
        expires_at = datetime.fromisoformat(expires_at_raw)
        needs_refresh = (expires_at - datetime.now(timezone.utc)).total_seconds() < 300

    if not needs_refresh:
        return decrypt_secret(encrypted_access, settings.secret_encryption_key)

    encrypted_refresh = metadata.get("oauth_refresh_token")
    if not encrypted_refresh:
        raise RuntimeError("Token TikTok expirado e sem refresh_token salvo — refaça a autorização em Integrações.")

    refresh_token = decrypt_secret(encrypted_refresh, settings.secret_encryption_key)
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"TikTok: falha ao renovar token ({payload.get('error_description', payload['error'])}).")

    from datetime import timedelta
    new_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 0)))).isoformat()
    new_metadata = {
        "oauth_access_token": encrypt_secret(payload["access_token"], settings.secret_encryption_key),
        "oauth_refresh_token": encrypt_secret(payload["refresh_token"], settings.secret_encryption_key) if payload.get("refresh_token") else metadata.get("oauth_refresh_token"),
        "oauth_expires_at": new_expires_at,
    }
    conn.execute(
        "update performance_connections set metadata = %s, updated_at = now() where id = %s",
        (Jsonb(new_metadata), connection["id"]),
    )
    return payload["access_token"]


def _list_videos(client: httpx.Client, access_token: str, date_from: date) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    items: list[dict[str, Any]] = []
    cursor = None
    while True:
        body: dict[str, Any] = {"max_count": 20}
        if cursor:
            body["cursor"] = cursor
        response = client.post(f"{VIDEO_LIST_URL}?fields={VIDEO_FIELDS}", headers=headers, json=body)
        response.raise_for_status()
        payload = response.json()
        error = payload.get("error") or {}
        if error.get("code") not in (None, "ok"):
            raise RuntimeError(f"TikTok API: {error.get('message', error)}")

        data = payload.get("data") or {}
        for video in data.get("videos", []):
            create_time = video.get("create_time")
            if create_time and datetime.fromtimestamp(create_time, tz=timezone.utc).date() < date_from:
                return items
            items.append(video)

        if not data.get("has_more"):
            break
        cursor = data.get("cursor")
    return items


def _row(workspace_id: UUID, client_id: UUID, item: dict[str, Any]) -> dict[str, Any]:
    create_time = item.get("create_time")
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "video_id": item["id"],
        "title": item.get("title"),
        "posted_at": datetime.fromtimestamp(create_time, tz=timezone.utc) if create_time else None,
        "view_count": int(item.get("view_count") or 0),
        "like_count": int(item.get("like_count") or 0),
        "comment_count": int(item.get("comment_count") or 0),
        "share_count": int(item.get("share_count") or 0),
    }
