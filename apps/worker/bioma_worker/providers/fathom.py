"""Cliente da API pública do Fathom (gravador de calls usado pela EG).

Documentação verificada em 2026-07-30:
- base: https://api.fathom.ai/external/v1
- auth: header `X-Api-Key`
- `GET /meetings` com `include_transcript`, `include_summary`,
  `include_action_items`, `created_after`, `cursor`; resposta paginada em
  `items` + `next_cursor`
- `GET /recordings/{recording_id}/transcript` devolve
  `{"transcript": [{"speaker": {"display_name"}, "text", "timestamp": "HH:MM:SS"}]}`
- limite de 60 chamadas/minuto por usuário

Sem FATHOM_API_KEY as funções FALHAM ALTO: transcrição de reunião é dado
sensível de cliente, não existe versão "prévia" plausível.
"""

from typing import Any

import httpx

BASE_URL = "https://api.fathom.ai/external/v1"


def _client(settings, http_client: httpx.Client | None) -> tuple[httpx.Client, bool]:
    if not settings.fathom_api_key:
        raise RuntimeError(
            "FATHOM_API_KEY não configurada no worker. Sem a chave o Bioma não tem como "
            "ler as reuniões reais — e não inventa transcrição."
        )
    if http_client is not None:
        return http_client, False
    return (
        httpx.Client(
            base_url=BASE_URL,
            headers={"X-Api-Key": settings.fathom_api_key},
            timeout=settings.fathom_request_timeout_seconds,
        ),
        True,
    )


def list_meetings(
    settings,
    created_after: str | None = None,
    limit: int = 20,
    http_client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Reuniões recentes, sem transcrição (payload leve para a tela de seleção)."""
    client, owns = _client(settings, http_client)
    meetings: list[dict[str, Any]] = []
    try:
        cursor: str | None = None
        while len(meetings) < limit:
            params: dict[str, Any] = {}
            if created_after:
                params["created_after"] = created_after
            if cursor:
                params["cursor"] = cursor
            response = client.get("/meetings", params=params)
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("items", []):
                meetings.append(_meeting_row(item))
                if len(meetings) >= limit:
                    break
            cursor = payload.get("next_cursor")
            if not cursor:
                break
    finally:
        if owns:
            client.close()
    return meetings


def get_meeting_transcript(
    settings,
    recording_id: int | str,
    http_client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Segmentos da transcrição, já normalizados para o formato do copiloto."""
    client, owns = _client(settings, http_client)
    try:
        response = client.get(f"/recordings/{recording_id}/transcript")
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns:
            client.close()

    segments: list[dict[str, Any]] = []
    for index, entry in enumerate(payload.get("transcript", [])):
        text = (entry.get("text") or "").strip()
        if not text:
            continue
        speaker = entry.get("speaker") or {}
        start_ms = _timestamp_to_ms(entry.get("timestamp"))
        segments.append(
            {
                # Idempotência real: reimportar a mesma reunião não duplica
                # segmento, porque a chave é estável (gravação + posição).
                "idempotency_key": f"fathom:{recording_id}:{index}",
                "source": "provider_webhook",
                "external_speaker_id": speaker.get("matched_calendar_invitee_email"),
                "speaker_label": speaker.get("display_name"),
                "start_ms": start_ms,
                "end_ms": None,
                "content": text[:20_000],
                "is_final": True,
            }
        )
    return segments


def _meeting_row(item: dict[str, Any]) -> dict[str, Any]:
    recorded_by = item.get("recorded_by") or {}
    invitees = item.get("calendar_invitees") or []
    return {
        "recording_id": item.get("recording_id"),
        "title": item.get("meeting_title") or item.get("title") or "Reunião sem título",
        "meeting_type": item.get("meeting_type"),
        "url": item.get("url") or item.get("share_url"),
        "created_at": item.get("created_at"),
        "started_at": item.get("recording_start_time") or item.get("scheduled_start_time"),
        "ended_at": item.get("recording_end_time") or item.get("scheduled_end_time"),
        "recorded_by": recorded_by.get("email"),
        # Convidados externos são a pista de qual cliente é a reunião.
        "external_invitees": [
            {"name": guest.get("name"), "email": guest.get("email"), "domain": guest.get("email_domain")}
            for guest in invitees
            if guest.get("is_external")
        ],
    }


def _timestamp_to_ms(value: Any) -> int:
    """"HH:MM:SS" -> milissegundos. Formato inesperado vira 0 (posição desconhecida),
    nunca um número inventado — a ordem real fica preservada pelo índice."""
    if not isinstance(value, str):
        return 0
    parts = value.split(":")
    try:
        numbers = [int(float(part)) for part in parts]
    except ValueError:
        return 0
    while len(numbers) < 3:
        numbers.insert(0, 0)
    hours, minutes, seconds = numbers[-3], numbers[-2], numbers[-1]
    return ((hours * 3600) + (minutes * 60) + seconds) * 1000
