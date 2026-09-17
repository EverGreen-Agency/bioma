from datetime import date, datetime
from typing import Any
from uuid import UUID

import httpx

from bioma_worker.storage import resolve_workspace_id, upsert_rows

# Nomes de métrica variam entre versões da Graph API e entre tipos de mídia —
# pedimos o conjunto mais amplo plausível e aceitamos o que vier; uma métrica
# ausente vira 0 (dado real "não disponível"), nunca um valor inventado.
FEED_METRICS = ("impressions", "reach", "saved", "shares")
VIDEO_METRICS = ("plays", "reach", "saved", "shares", "ig_reels_avg_watch_time", "avg_watch_time")

UPSERT_COLUMNS = (
    "workspace_id", "client_id", "ig_media_id", "permalink", "media_type", "caption",
    "posted_at", "media_url", "thumbnail_url", "reach", "impressions", "likes",
    "comments", "shares", "saved", "plays", "avg_watch_time_seconds",
)


def sync(
    conn,
    client: httpx.Client,
    settings,
    client_id: UUID,
    connection: dict[str, Any],
    date_from: date,
    date_to: date,
) -> int:
    access_token = settings.instagram_access_token
    if not access_token:
        raise RuntimeError("INSTAGRAM_ACCESS_TOKEN não configurado no worker.")

    ig_account_id = connection["external_account_id"]
    media_endpoint = f"https://graph.facebook.com/{settings.instagram_api_version}/{ig_account_id}/media"
    params = {
        "access_token": access_token,
        "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,like_count,comments_count",
        "limit": str(settings.instagram_post_sync_limit),
    }

    items = _fetch_media(client, media_endpoint, params, date_from)
    workspace_id = resolve_workspace_id(conn, client_id)

    rows = []
    for item in items:
        insights = _fetch_insights(client, settings, access_token, item)
        rows.append(_row(workspace_id, client_id, item, insights))

    count = upsert_rows(conn, "workspace_instagram_posts", UPSERT_COLUMNS, ("workspace_id", "ig_media_id"), rows)

    if settings.openai_api_key:
        _transcribe_pending(conn, client, settings, workspace_id)

    return count


def _fetch_media(client: httpx.Client, endpoint: str, params: dict[str, str], date_from: date) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    url: str | None = endpoint
    request_params: dict[str, str] | None = params
    while url:
        response = client.get(url, params=request_params)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(f"Instagram Graph API: {payload['error'].get('message', payload['error'])}")
        for item in payload.get("data", []):
            posted_at = _parse_timestamp(item.get("timestamp"))
            if posted_at and posted_at.date() < date_from:
                return items
            items.append(item)
        next_url = payload.get("paging", {}).get("next")
        url = next_url
        request_params = None
    return items


def _fetch_insights(client: httpx.Client, settings, access_token: str, item: dict[str, Any]) -> dict[str, float]:
    media_type = (item.get("media_type") or "").upper()
    metrics = VIDEO_METRICS if media_type in ("VIDEO", "REELS") else FEED_METRICS
    endpoint = f"https://graph.facebook.com/{settings.instagram_api_version}/{item['id']}/insights"
    try:
        response = client.get(endpoint, params={"access_token": access_token, "metric": ",".join(metrics)})
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            return {}
        return {
            entry["name"]: (entry.get("values") or [{}])[0].get("value", 0)
            for entry in payload.get("data", [])
        }
    except httpx.HTTPError:
        # Uma falha pontual de insights não pode derrubar a sincronização do
        # post inteiro — o post fica com métricas zeradas (dado real ausente).
        return {}


def _row(workspace_id: UUID, client_id: UUID, item: dict[str, Any], insights: dict[str, float]) -> dict[str, Any]:
    watch_time_ms = insights.get("ig_reels_avg_watch_time") or insights.get("avg_watch_time")
    return {
        "workspace_id": workspace_id,
        "client_id": client_id,
        "ig_media_id": item["id"],
        "permalink": item.get("permalink"),
        "media_type": item.get("media_type") or "IMAGE",
        "caption": item.get("caption"),
        "posted_at": _parse_timestamp(item.get("timestamp")),
        "media_url": item.get("media_url"),
        "thumbnail_url": item.get("thumbnail_url"),
        "reach": int(insights.get("reach") or 0),
        "impressions": int(insights.get("impressions") or 0),
        "likes": int(item.get("like_count") or 0),
        "comments": int(item.get("comments_count") or 0),
        "shares": int(insights.get("shares") or 0),
        "saved": int(insights.get("saved") or 0),
        "plays": int(insights.get("plays") or 0),
        "avg_watch_time_seconds": round(watch_time_ms / 1000, 2) if watch_time_ms else None,
    }


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _transcribe_pending(conn, client: httpx.Client, settings, workspace_id: UUID) -> None:
    pending = conn.execute(
        """
        select id, media_url from workspace_instagram_posts
        where workspace_id = %s and media_type in ('VIDEO', 'REELS')
          and transcript is null and media_url is not null
        order by posted_at desc
        limit 20
        """,
        (workspace_id,),
    ).fetchall()

    for post in pending:
        try:
            transcript = _transcribe_video(client, settings, post["media_url"])
        except httpx.HTTPError as exc:
            # Vídeo pode já ter expirado na CDN da Meta (media_url tem TTL curto);
            # não é erro fatal do sync, só fica sem transcrição desta vez.
            transcript = None
            _ = exc
        if transcript:
            conn.execute(
                "update workspace_instagram_posts set transcript = %s, transcript_generated_at = now() where id = %s",
                (transcript, post["id"]),
            )


def _transcribe_video(client: httpx.Client, settings, media_url: str) -> str | None:
    video_response = client.get(media_url, timeout=60)
    video_response.raise_for_status()

    files = {"file": ("post.mp4", video_response.content, "video/mp4")}
    data = {"model": settings.openai_transcription_model}
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    response = httpx.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers=headers,
        data=data,
        files=files,
        timeout=settings.openai_request_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("text")
