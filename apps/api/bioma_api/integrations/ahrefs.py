import httpx

BASE_URL = "https://api.ahrefs.com/v3/social-media"


class AhrefsError(RuntimeError):
    pass


class AhrefsClient:
    """Benchmark de concorrentes via Ahrefs Social Media API v3.

    Só enxerga canais que já foram conectados no workspace Ahrefs da EG —
    não existe lookup de handle arbitrário nesta API. Conectar o perfil
    público do concorrente no Ahrefs é um passo manual, análogo a configurar
    um token de qualquer outra integração.
    """

    def __init__(self, api_key: str, http_client: httpx.Client | None = None):
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=BASE_URL,
            timeout=20,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def find_channel(self, handle: str) -> dict | None:
        payload = self._get("/channels")
        needle = handle.lstrip("@").lower()
        for channel in payload.get("channels", []):
            if str(channel.get("channel_username", "")).lstrip("@").lower() == needle:
                return channel
        return None

    def top_posts(self, channel_id: str, date_from: str, date_to: str, limit: int = 10) -> list[dict]:
        payload = self._get(
            "/posts",
            params={
                "status": "published",
                "channel_ids": channel_id,
                "date_from": date_from,
                "date_to": date_to,
                "order_by": "likes",
                "order_direction": "desc",
                "limit": limit,
            },
        )
        posts = payload.get("posts", [])
        enriched = []
        for post in posts:
            metrics = self._post_metrics(post, channel_id, date_from, date_to)
            enriched.append({
                "text_content": post.get("text_content"),
                "permalink": post.get("permalink"),
                "created_at": post.get("created_at"),
                "likes": metrics.get("likes", 0),
                "comments": (metrics.get("instagram_metrics") or {}).get("comments", 0),
                "shares": (metrics.get("instagram_metrics") or {}).get("shares", 0),
                "saved": (metrics.get("instagram_metrics") or {}).get("saved", 0),
            })
        return enriched

    def _post_metrics(self, post: dict, channel_id: str, date_from: str, date_to: str) -> dict:
        external_id = post.get("external_post_id")
        if not external_id:
            return {}
        try:
            payload = self._get(
                "/post-metrics",
                params={
                    "external_post_id": external_id,
                    "channel_id": channel_id,
                    "date_from": date_from,
                    "date_to": date_to,
                },
            )
            values = payload.get("metrics") or []
            return values[0] if values else {}
        except AhrefsError:
            # Um post sem métricas disponíveis não deve derrubar o benchmark inteiro.
            return {}

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            response = self._client.get(path, params=params or {})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise AhrefsError(f"Ahrefs API: {exc}") from exc
