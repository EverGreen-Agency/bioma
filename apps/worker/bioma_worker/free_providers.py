from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import httpx

from bioma_worker.crypto import decrypt_secret


FREE_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "default_env_var": "GROQ_API_KEY",
        "description": "Inferência LPU ultra-rápida (~200ms de latência). Tier gratuito generoso.",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        "default_model": "llama-3.3-70b-versatile",
    },
    "cerebras": {
        "name": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "default_env_var": "CEREBRAS_API_KEY",
        "description": "Chip Wafer-Scale CS-3 (~2000 tokens/s). 1 milhão de tokens grátis por dia.",
        "models": [
            "llama3.1-8b",
            "llama3.1-70b",
        ],
        "default_model": "llama3.1-70b",
    },
    "sambanova": {
        "name": "SambaNova Systems",
        "base_url": "https://api.sambanova.ai/v1",
        "default_env_var": "SAMBANOVA_API_KEY",
        "description": "Aceleradores SN40L com modelos de fronteira e reasoning sem custo.",
        "models": [
            "Meta-Llama-3.3-70B-Instruct",
            "DeepSeek-R1-Distill-Llama-70B",
            "Qwen2.5-72B-Instruct",
        ],
        "default_model": "Meta-Llama-3.3-70B-Instruct",
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "default_env_var": "MISTRAL_API_KEY",
        "description": "Modelos europeus de alta qualidade com plano de testes gratuito.",
        "models": [
            "mistral-small-latest",
            "codestral-latest",
            "open-mistral-nemo",
        ],
        "default_model": "mistral-small-latest",
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "default_env_var": "TOGETHER_API_KEY",
        "description": "Plataforma de modelos abertos com tier de avaliação gratuito.",
        "models": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        ],
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    },
    "cohere": {
        "name": "Cohere",
        "base_url": "https://api.cohere.com/v2",
        "default_env_var": "COHERE_API_KEY",
        "description": "Especialista em RAG e geração de texto corporativa (Command R).",
        "models": [
            "command-r",
            "command-r-plus",
        ],
        "default_model": "command-r",
    },
    "github_models": {
        "name": "GitHub Models",
        "base_url": "https://models.inference.ai.azure.com",
        "default_env_var": "GITHUB_TOKEN",
        "description": "Acesso gratuito aos modelos OpenAI e Llama via GitHub Personal Access Token.",
        "models": [
            "gpt-4o-mini",
            "Meta-Llama-3.1-70B-Instruct",
        ],
        "default_model": "gpt-4o-mini",
    },
    "cloudflare": {
        "name": "Cloudflare Workers AI",
        "base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        "default_env_var": "CLOUDFLARE_API_TOKEN",
        "description": "Inferência edge serverless com 10.000 neurônios gratuitos diários.",
        "models": [
            "@cf/meta/llama-3.3-70b-instruct",
            "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
        ],
        "default_model": "@cf/meta/llama-3.3-70b-instruct",
    },
    "deepinfra": {
        "name": "DeepInfra",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "default_env_var": "DEEPINFRA_API_KEY",
        "description": "Infraestrutura escalável para open-source com créditos iniciais gratuitos.",
        "models": [
            "meta-llama/Meta-Llama-3.3-70B-Instruct",
            "deepseek-ai/DeepSeek-R1",
        ],
        "default_model": "meta-llama/Meta-Llama-3.3-70B-Instruct",
    },
    "novita": {
        "name": "Novita AI",
        "base_url": "https://api.novita.ai/v3/openai",
        "default_env_var": "NOVITA_API_KEY",
        "description": "Aceleradores de alta eficiência para Llama 3 e DeepSeek.",
        "models": [
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-r1",
        ],
        "default_model": "meta-llama/llama-3.3-70b-instruct",
    },
}


def make_key_fingerprint(api_key: str) -> str:
    cleaned = api_key.strip()
    if len(cleaned) <= 8:
        return "***"
    return f"{cleaned[:4]}...{cleaned[-4:]}"


def get_active_provider_key(conn, provider_code: str, secret_encryption_key: str) -> tuple[str, str | None]:
    preset = FREE_PROVIDER_PRESETS.get(provider_code)
    if not preset:
        raise ValueError(f"Provedor gratuito não reconhecido: {provider_code}")

    if conn is not None:
        try:
            row = conn.execute(
                """
                SELECT id, key_encrypted
                FROM ai_provider_key_pool
                WHERE provider_code = %s
                  AND status = 'active'
                  AND (cooldown_until IS NULL OR cooldown_until <= now())
                ORDER BY last_used_at ASC NULLS FIRST, call_count ASC
                LIMIT 1
                """,
                (provider_code,),
            ).fetchone()
            if row:
                key_id = str(row["id"]) if isinstance(row, dict) else str(row[0])
                encrypted = row["key_encrypted"] if isinstance(row, dict) else row[1]
                decrypted = decrypt_secret(encrypted, secret_encryption_key)
                if decrypted:
                    return decrypted, key_id
        except Exception:
            # Fallback para variável de ambiente se tabela ou consulta falhar
            pass

    env_var_name = preset.get("default_env_var")
    if env_var_name:
        env_val = os.environ.get(env_var_name)
        if env_val:
            return env_val.strip(), None

    raise RuntimeError(
        f"Nenhuma chave ativa ou variável de ambiente ({env_var_name}) encontrada para o provedor {preset['name']}."
    )


def record_key_success(conn, key_id: str | None) -> None:
    if not conn or not key_id:
        return
    try:
        conn.execute(
            """
            UPDATE ai_provider_key_pool
            SET call_count = call_count + 1,
                last_used_at = now(),
                error_count = 0,
                status = 'active'
            WHERE id = %s
            """,
            (key_id,),
        )
    except Exception:
        pass


def record_key_rate_limit(conn, key_id: str | None, error_message: str, cooldown_seconds: int = 60) -> None:
    if not conn or not key_id:
        return
    try:
        conn.execute(
            """
            UPDATE ai_provider_key_pool
            SET error_count = error_count + 1,
                last_error_at = now(),
                last_error_message = %s,
                status = 'cooldown',
                cooldown_until = now() + (interval '1 second' * %s)
            WHERE id = %s
            """,
            (error_message[:2000], cooldown_seconds, key_id),
        )
    except Exception:
        pass


def execute_free_provider_call(
    provider_code: str,
    model_id: str,
    prompt: str,
    settings,
    conn=None,
    extra_headers: dict[str, str] | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    preset = FREE_PROVIDER_PRESETS.get(provider_code)
    if not preset:
        raise ValueError(f"Provedor gratuito desconhecido: {provider_code}")

    base_url = preset["base_url"].rstrip("/")
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    request_payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
    }

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        api_key, key_id = get_active_provider_key(conn, provider_code, settings.secret_encryption_key)
        headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = httpx.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=request_payload,
                timeout=getattr(settings, "ai_execution_timeout_seconds", 60),
            )
            if response.status_code == 429:
                err_text = response.text[:500]
                record_key_rate_limit(conn, key_id, f"HTTP 429: {err_text}", cooldown_seconds=60)
                last_error = RuntimeError(f"{preset['name']} retornou 429 (Rate Limit): {err_text}")
                continue

            response.raise_for_status()
            payload = response.json()
            record_key_success(conn, key_id)

            usage = payload.get("usage") or {}
            choices = payload.get("choices") or []
            message_text = ""
            if choices:
                message_text = choices[0].get("message", {}).get("content") or ""

            return {
                "text": message_text,
                "usage": {
                    "input_units": usage.get("prompt_tokens"),
                    "output_units": usage.get("completion_tokens"),
                    "cached_units": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                },
                "cost_cents": 0,
                "currency": "USD",
                "external_event_id": payload.get("id"),
                "metadata": {
                    "provider": provider_code,
                    "model": model_id,
                    "served_model": payload.get("model") or model_id,
                    "provider_name": preset["name"],
                },
            }

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                record_key_rate_limit(conn, key_id, str(exc), cooldown_seconds=60)
                last_error = exc
                continue
            detail = exc.response.text.strip()[-1000:]
            raise RuntimeError(f"{preset['name']} erro HTTP {exc.response.status_code}: {detail}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            break

    if last_error:
        raise RuntimeError(f"Todas as tentativas para {preset['name']} falharam: {last_error}") from last_error
    raise RuntimeError(f"Falha ao executar chamada para {preset['name']}")
