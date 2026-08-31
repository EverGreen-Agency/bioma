from datetime import date
from typing import Any
from uuid import UUID

import httpx

from bioma_worker.storage import resolve_workspace_id, upsert_rows

# Estatísticas de canal/vídeo do YouTube são dados públicos — só precisa de
# uma API key simples (sem OAuth/service account), diferente de todo o resto
# do ecossistema Google usado neste worker.


def sync(
    conn,
    client: httpx.Client,
    settings,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    api_key = settings.youtube_api_key
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY não configurado no worker.")

    channel_id = connection["external_account_id"]
    video_ids = _list_recent_video_ids(client, api_key, channel_id, date_from, date_to, settings.youtube_organic_sync_limit)
    if not video_ids:
        return 0

    items = _fetch_video_stats(client, api_key, video_ids)
    workspace_id = resolve_workspace_id(conn, client_id)

    rows = [_row(workspace_id, client_id, channel_id, item) for item in items]
    return upsert_rows(
        conn,
        "workspace_youtube_organic_videos",
        ("workspace_id", "client_id", "video_id", "channel_id", "title", "published_at", "view_count", "like_count", "comment_count"),
        ("workspace_id", "video_id"),
        rows,
    )


def _list_recent_video_ids(
    client: httpx.Client, api_key: str, channel_id: str, date_from: date, date_to: date, limit: int,
) -> list[str]:
    params = {
        "key": api_key,
        "channelId": channel_id,
        "part": "id",
        "type": "video",
        "order": "date",
        "maxResults": min(limit, 50),
        "publishedAfter": f"{date_from.isoformat()}T00:00:00Z",
        "publishedBefore": f"{date_to.isoformat()}T23:59:59Z",
    }
    response = client.get("https://www.googleapis.com/youtube/v3/search", params=params)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"YouTube Data API: {payload['error'].get('message', payload['error'])}")
    return [
        item["id"]["videoId"]
        for item in payload.get("items", [])
        if item.get("id", {}).get("videoId")
    ]


def _fetch_video_stats(client: httpx.Client, api_key: str, video_ids: list[str]) -> list[dict[str, Any]]:
    response = client.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"key": api_key, "id": ",".join(video_ids), "part": "snippet,statistics"},
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"YouTube Data API: {payload['error'].get('message', payload['error'])}")
    return payload.get("items", [])


def _row(workspace_id: UUID, client_id: UUID, channel_id: str, item: dict[str, Any]) -> dict[str, Any]:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "video_id": item["id"],
        "channel_id": channel_id,
        "title": snippet.get("title"),
        "published_at": snippet.get("publishedAt"),
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
    }
