"""Transcrição de áudio anexado ao copiloto, via Whisper (OpenAI).

Mesmo contrato já usado em `providers/instagram_organic.py` para transcrever
Reels — reaproveitado aqui em vez de reinventado.

Sem `OPENAI_API_KEY` levanta: um anexo de áudio sem transcrição real fica
marcado como "não foi possível transcrever", nunca com um texto inventado no
lugar do que a pessoa falou.
"""

from __future__ import annotations

from typing import Any

import httpx


def transcribe_audio(
    content: bytes,
    file_name: str,
    content_type: str,
    settings,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Devolve `{text, provider, model}`. Levanta `RuntimeError`/`httpx.HTTPError`
    sem chave ou em falha da API — quem chama decide como comunicar isso."""
    if not settings.openai_api_key:
        raise RuntimeError("Transcrição de áudio exige OPENAI_API_KEY.")

    files = {"file": (file_name or "audio", content, content_type or "application/octet-stream")}
    data = {"model": settings.openai_transcription_model}
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=settings.openai_request_timeout_seconds)
    try:
        response = client.post(
            "https://api.openai.com/v1/audio/transcriptions", headers=headers, data=data, files=files
        )
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            client.close()

    return {
        "text": (payload.get("text") or "").strip(),
        "provider": "openai",
        "model": settings.openai_transcription_model,
    }
