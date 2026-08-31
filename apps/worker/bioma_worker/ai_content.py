import json
from typing import Any

import httpx

# Schemas de saída por tipo de conteúdo
OUTPUT_SCHEMA_POSTS = {
    "type": "object",
    "additionalProperties": False,
    "required": ["strategy_note", "posts"],
    "properties": {
        "strategy_note": {"type": "string"},
        "posts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "channel", "format", "hook", "caption", "cta"],
                "properties": {
                    "title": {"type": "string"},
                    "channel": {
                        "type": "string",
                        "enum": ["instagram", "linkedin", "facebook", "tiktok", "youtube"],
                    },
                    "format": {"type": "string"},
                    "hook": {"type": "string"},
                    "caption": {"type": "string"},
                    "cta": {"type": "string"},
                },
            },
        },
    },
}

OUTPUT_SCHEMA_IMAGES = {
    "type": "object",
    "additionalProperties": False,
    "required": ["strategy_note", "images"],
    "properties": {
        "strategy_note": {"type": "string"},
        "images": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "channel", "aspect_ratio", "visual_description", "prompt_en", "provider"],
                "properties": {
                    "title": {"type": "string"},
                    "channel": {
                        "type": "string",
                        "enum": ["instagram", "linkedin", "facebook", "tiktok", "youtube"],
                    },
                    "aspect_ratio": {"type": "string", "enum": ["1:1", "9:16", "16:9"]},
                    "visual_description": {"type": "string"},
                    "prompt_en": {"type": "string"},
                    "provider": {"type": "string"},
                    "preview_url": {"type": ["string", "null"]},
                },
            },
        },
    },
}

OUTPUT_SCHEMA_VIDEO_SCRIPTS = {
    "type": "object",
    "additionalProperties": False,
    "required": ["strategy_note", "video_scripts"],
    "properties": {
        "strategy_note": {"type": "string"},
        "video_scripts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "title",
                    "channel",
                    "format",
                    "duration_seconds",
                    "hook_0_3s",
                    "script_body",
                    "cta_final",
                    "broll_notes",
                ],
                "properties": {
                    "title": {"type": "string"},
                    "channel": {
                        "type": "string",
                        "enum": ["instagram", "linkedin", "facebook", "tiktok", "youtube"],
                    },
                    "format": {"type": "string"},
                    "duration_seconds": {"type": "integer"},
                    "hook_0_3s": {"type": "string"},
                    "script_body": {"type": "string"},
                    "cta_final": {"type": "string"},
                    "broll_notes": {"type": "string"},
                    "camera_angle_notes": {"type": ["string", "null"]},
                },
            },
        },
    },
}


def generate_content(request: dict[str, Any], settings, http_client: httpx.Client | None = None) -> dict[str, Any]:
    content_type = request.get("content_type", "social_posts")
    if not settings.openai_api_key:
        return {
            "provider": "local_preview",
            "model": "methodology-preview-v1",
            "generation_mode": "preview",
            "output": _preview_output(request),
        }

    schema = OUTPUT_SCHEMA_POSTS
    schema_name = "bioma_social_content"
    if content_type == "image_generation":
        schema = OUTPUT_SCHEMA_IMAGES
        schema_name = "bioma_image_generation"
    elif content_type == "video_scripts":
        schema = OUTPUT_SCHEMA_VIDEO_SCRIPTS
        schema_name = "bioma_video_scripts"

    payload = {
        "model": settings.openai_model,
        "instructions": (
            "Você é o estúdio de conteúdo IA multimodal da EverGreen. Gere peças profissionais em português do Brasil "
            "específicas para o briefing fornecido. Para imagens, crie prompts em inglês de alta fidelidade visual (DALL-E 3/Flux/Higgsfield). "
            "Para vídeos, estruture o roteiro com Hook nos primeiros 3s, corpo com B-rolls marcadas e CTA de conversão."
        ),
        "input": json.dumps(
            {
                "content_type": content_type,
                "brief": request["brief"],
                "channels": request["channels"],
                "quantity": request["quantity"],
                "tone": request.get("tone"),
                "objective": request.get("objective"),
                "methodology_refs": request.get("methodology_refs", []),
                "image_provider": request.get("image_provider", "dalle_3"),
            },
            ensure_ascii=False,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
        "max_output_tokens": 5000,
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    owns_client = http_client is None
    client = http_client or httpx.Client(
        base_url="https://api.openai.com",
        timeout=settings.openai_request_timeout_seconds,
    )
    try:
        response = client.post("/v1/responses", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
    finally:
        if owns_client:
            client.close()

    output = json.loads(_output_text(response_data))
    return {
        "provider": "openai",
        "model": response_data.get("model") or settings.openai_model,
        "generation_mode": "live",
        "output": output,
        "response_id": response_data.get("id"),
        "usage": response_data.get("usage") or {},
    }


def _output_text(response_data: dict[str, Any]) -> str:
    if isinstance(response_data.get("output_text"), str):
        return response_data["output_text"]
    for item in response_data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise RuntimeError("A resposta do provedor não contém output_text.")


def _preview_output(request: dict[str, Any]) -> dict[str, Any]:
    content_type = request.get("content_type", "social_posts")
    channels = request["channels"]
    objective = request.get("objective") or "iniciar uma conversa relevante de alto valor"
    tone = request.get("tone") or "estratégico, claro e institucional"
    img_provider = request.get("image_provider") or "dalle_3"

    if content_type == "image_generation":
        images = []
        for index in range(request["quantity"]):
            channel = channels[index % len(channels)]
            aspect = "9:16" if channel in ["instagram", "tiktok"] else "1:1"
            images.append(
                {
                    "title": f"Arte Visual #{index + 1}: {objective[:50]}",
                    "channel": channel,
                    "aspect_ratio": aspect,
                    "visual_description": f"Design editorial moderno em estilo {tone}. Foco visual em autoridade e crescimento.",
                    "prompt_en": f"High resolution, photorealistic corporate image for {channel}, modern aesthetic, style {tone}, subject: {request['brief'][:100]} --ar {aspect.replace(':', '___')}",
                    "provider": img_provider,
                    "preview_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80",
                }
            )
        return {
            "strategy_note": f"Diretrizes visuais para artes ({img_provider}). Configure OPENAI_API_KEY no worker para geração live.",
            "images": images,
        }

    elif content_type == "video_scripts":
        scripts = []
        for index in range(request["quantity"]):
            channel = channels[index % len(channels)]
            scripts.append(
                {
                    "title": f"Roteiro de Vídeo #{index + 1}: {objective[:50]}",
                    "channel": channel,
                    "format": "reels" if channel == "instagram" else ("tiktok" if channel == "tiktok" else "video_ad"),
                    "duration_seconds": 45,
                    "hook_0_3s": f"Você sabia que 80% das empresas erram ao {objective.lower()}?",
                    "script_body": (
                        f"Locução ({tone}): Aqui está o método de 3 passos da EverGreen:\n"
                        f"1. Diagnóstico do gargalo comercial.\n"
                        f"2. Alinhamento da Oferta, Demanda e Conversão.\n"
                        f"3. Execução em Sprints de 90 dias.\n"
                        f"Briefing: {request['brief'][:300]}"
                    ),
                    "cta_final": "Toque no link da bio e agende o Raio-X Comercial com nosso time de especialistas.",
                    "broll_notes": "[0-3s] Tela dividida com gráficos em queda / [3-30s] Especialista em estúdio com dashboard do Bioma / [30-45s] Animação do logo EverGreen com QR Code.",
                    "camera_angle_notes": "Plano médio fixo com luz lateral suave, cortes dinâmicos a cada 4 segundos.",
                }
            )
        return {
            "strategy_note": "Roteiros de alta conversão estruturados para vídeos e anúncios. Configure OPENAI_API_KEY para expansão live.",
            "video_scripts": scripts,
        }

    else:
        posts = []
        for index in range(request["quantity"]):
            channel = channels[index % len(channels)]
            posts.append(
                {
                    "title": f"Rascunho {index + 1}: {objective[:60]}",
                    "channel": channel,
                    "format": "post estático" if channel != "tiktok" else "roteiro curto",
                    "hook": f"E se o próximo passo para {objective.lower()} fosse mais simples?",
                    "caption": (
                        f"Ponto de partida editorial em tom {tone}.\n\n"
                        f"Briefing: {request['brief'][:500]}\n\n"
                        "Revise fatos, exemplos e voz da marca antes de publicar."
                    ),
                    "cta": "Converse com a equipe e transforme este rascunho em uma peça final.",
                }
            )
        return {
            "strategy_note": "Prévia metodológica local. Configure OPENAI_API_KEY no worker para geração real.",
            "posts": posts,
        }
