import asyncio
import json
import os
import subprocess
import time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import httpx

from bioma_worker.provider_credentials import provider_process_environment


class ProviderExecutionError(RuntimeError):
    pass


def build_prompt(job: dict[str, Any]) -> str:
    input_json = json.dumps(job.get("workflow_input") or {}, ensure_ascii=False, indent=2, default=str)
    previous_json = json.dumps(job.get("previous_outputs") or {}, ensure_ascii=False, indent=2, default=str)
    return f"""Você está executando uma etapa interna e auditável do Bioma.

Workflow: {job["definition_name"]} ({job["definition_slug"]})
Etapa: {job["name"]} [{job["step_key"]}]
Objetivo da etapa: {job.get("description") or "Não informado"}
Capacidade esperada: {job.get("capability") or "content"}

Entrada original:
{input_json}

Saídas já aprovadas ou concluídas:
{previous_json}

Produza somente a entrega desta etapa em Markdown. Não invente dados, fontes,
aprovações ou ações externas. Separe explicitamente fatos fornecidos, hipóteses
e lacunas que precisam de validação humana. Não diga que publicou, configurou,
enviou ou alterou sistemas externos."""


def _working_directory(candidate: dict[str, Any]) -> str | None:
    configured = (candidate.get("account_settings") or {}).get("working_directory")
    if not configured:
        return None
    path = Path(configured).expanduser()
    if not path.is_dir():
        raise ProviderExecutionError(f"working_directory configurado não existe: {path}")
    return str(path)


def _run_process(
    command: list[str],
    prompt: str,
    timeout_seconds: int,
    cwd: str | None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            cwd=cwd,
            env=env,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise ProviderExecutionError(f"Executável não encontrado: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProviderExecutionError(f"Provider excedeu o timeout de {timeout_seconds}s.") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "falha sem detalhe").strip()[-2000:]
        raise ProviderExecutionError(f"{command[0]} terminou com código {result.returncode}: {detail}")
    return result

def parse_codex_jsonl(raw: str) -> dict[str, Any]:
    texts: list[str] = []
    usage: dict[str, Any] = {}
    external_event_id: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        item = event.get("item") or {}
        if event_type == "item.completed" and item.get("type") == "agent_message" and item.get("text"):
            texts.append(item["text"])
        if event_type == "thread.started":
            external_event_id = event.get("thread_id") or event.get("id")
        if event_type == "turn.completed":
            raw_usage = event.get("usage") or {}
            usage = {
                "input_units": raw_usage.get("input_tokens"),
                "output_units": raw_usage.get("output_tokens"),
                "cached_units": raw_usage.get("cached_input_tokens"),
            }
    text = "\n\n".join(texts).strip()
    if not text:
        raise ProviderExecutionError("Codex não retornou uma mensagem final reconhecível.")
    return {"text": text, "usage": usage, "external_event_id": external_event_id}


def execute_codex(candidate: dict[str, Any], prompt: str, settings) -> dict[str, Any]:
    binary = (candidate.get("account_settings") or {}).get("binary_path") or settings.codex_cli_path
    command = [
        binary,
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--model",
        candidate["model_id"],
        "-",
    ]
    with provider_process_environment(candidate, settings) as process_env:
        result = _run_process(
            command,
            prompt,
            settings.ai_execution_timeout_seconds,
            _working_directory(candidate),
            process_env,
        )
    return parse_codex_jsonl(result.stdout)


def parse_claude_json(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderExecutionError("Claude Code não retornou JSON válido.") from exc
    text = payload.get("result")
    if not isinstance(text, str) or not text.strip():
        raise ProviderExecutionError("Claude Code não retornou uma mensagem final reconhecível.")
    raw_usage = payload.get("usage") or {}
    cost_usd = payload.get("total_cost_usd")
    cost_cents = None
    if cost_usd is not None:
        cost_cents = int((Decimal(str(cost_usd)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return {
        "text": text.strip(),
        "usage": {
            "input_units": raw_usage.get("input_tokens"),
            "output_units": raw_usage.get("output_tokens"),
            "cached_units": raw_usage.get("cache_read_input_tokens"),
        },
        "cost_cents": cost_cents,
        "currency": "USD",
        "external_event_id": payload.get("session_id"),
        "metadata": {"subtype": payload.get("subtype"), "num_turns": payload.get("num_turns")},
    }


def execute_claude(candidate: dict[str, Any], prompt: str, settings) -> dict[str, Any]:
    binary = (candidate.get("account_settings") or {}).get("binary_path") or settings.claude_cli_path
    command = [
        binary,
        "-p",
        "--output-format",
        "json",
        "--model",
        candidate["model_id"],
        "--tools",
        "",
    ]
    with provider_process_environment(candidate, settings) as process_env:
        result = _run_process(
            command,
            prompt,
            settings.ai_execution_timeout_seconds,
            _working_directory(candidate),
            process_env,
        )
    return parse_claude_json(result.stdout)


def parse_antigravity_json(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderExecutionError("Antigravity CLI não retornou JSON válido.") from exc
    if payload.get("status") != "SUCCESS":
        raise ProviderExecutionError(
            f"Antigravity CLI encerrou sem sucesso: {payload.get('error') or payload.get('status') or 'erro desconhecido'}"
        )
    text = payload.get("response")
    if not isinstance(text, str) or not text.strip():
        raise ProviderExecutionError("Antigravity CLI não retornou uma mensagem final reconhecível.")
    usage = payload.get("usage") or {}
    return {
        "text": text.strip(),
        "usage": {
            "input_units": usage.get("input_tokens"),
            "output_units": usage.get("output_tokens"),
            "cached_units": usage.get("cache_read_tokens"),
        },
        "external_event_id": payload.get("conversation_id"),
        "metadata": {
            "thinking_units": usage.get("thinking_tokens"),
            "num_turns": payload.get("num_turns"),
        },
    }


def execute_antigravity_cli(candidate: dict[str, Any], prompt: str, settings) -> dict[str, Any]:
    binary = (candidate.get("account_settings") or {}).get("binary_path") or settings.antigravity_cli_path
    command = [
        binary,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--model",
        candidate["model_id"],
        "--sandbox",
        "--print-timeout",
        f"{settings.ai_execution_timeout_seconds}s",
    ]
    with provider_process_environment(candidate, settings) as process_env:
        result = _run_process(
            command,
            "",
            settings.ai_execution_timeout_seconds + 10,
            _working_directory(candidate),
            process_env,
        )
    return parse_antigravity_json(result.stdout)


def _env_auth_value(candidate: dict[str, Any], fallback: str | None) -> str | None:
    auth_ref = candidate.get("auth_ref")
    if auth_ref and auth_ref.startswith("env:"):
        return os.environ.get(auth_ref.removeprefix("env:"))
    return fallback


def _usage_value(usage: Any, *names: str) -> int | None:
    if usage is None:
        return None
    for name in names:
        value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
        if value is not None:
            return int(value)
    return None


def _message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ProviderExecutionError("Provider API respondeu sem choices.")
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        text = "\n".join(
            str(part.get("text") or "")
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
        ).strip()
        if text:
            return text
    raise ProviderExecutionError("Provider API não retornou texto reconhecível.")


def execute_openai_compatible(candidate: dict[str, Any], prompt: str, settings) -> dict[str, Any]:
    channel = candidate["channel"]
    if channel == "openrouter":
        api_key = _env_auth_value(candidate, settings.openrouter_api_key)
        base_url = settings.openrouter_base_url
        headers = {
            "HTTP-Referer": settings.openrouter_site_url,
            "X-OpenRouter-Title": settings.openrouter_app_name,
            "X-OpenRouter-Metadata": "enabled",
        }
    elif channel == "deepseek":
        api_key = _env_auth_value(candidate, settings.deepseek_api_key)
        base_url = settings.deepseek_base_url
        headers = {}
    else:
        raise ProviderExecutionError(f"Canal API incompatível: {channel}")
    if not api_key:
        env_name = "OPENROUTER_API_KEY" if channel == "openrouter" else "DEEPSEEK_API_KEY"
        raise ProviderExecutionError(
            f"Credencial {channel} ausente. Configure auth_ref=env:{env_name} e o secret no runtime."
        )
    request_payload: dict[str, Any] = {
        "model": candidate["model_id"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
    }
    if channel == "deepseek" and candidate["model_id"] in {"deepseek-v4-flash", "deepseek-v4-pro"}:
        request_payload["thinking"] = {
            "type": "enabled" if "reasoning" in (candidate.get("model_capabilities") or []) else "disabled"
        }
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **headers},
            json=request_payload,
            timeout=settings.ai_execution_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()[-1600:]
        raise ProviderExecutionError(f"{channel} respondeu HTTP {exc.response.status_code}: {detail}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderExecutionError(f"Falha ao chamar {channel}: {exc}") from exc
    usage = payload.get("usage") or {}
    cost = usage.get("cost")
    cost_cents = None
    if cost is not None:
        cost_cents = int((Decimal(str(cost)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return {
        "text": _message_text(payload),
        "usage": {
            "input_units": usage.get("prompt_tokens"),
            "output_units": usage.get("completion_tokens"),
            "cached_units": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
        },
        "cost_cents": cost_cents,
        "currency": "USD",
        "external_event_id": payload.get("id"),
        "metadata": {
            "served_model": payload.get("model"),
            "service_tier": payload.get("service_tier"),
        },
    }


async def _execute_antigravity_async(candidate: dict[str, Any], prompt: str, settings) -> dict[str, Any]:
    try:
        from google.antigravity import Agent, LocalAgentConfig
    except ImportError as exc:
        raise ProviderExecutionError(
            "Antigravity SDK não instalado no worker; instale a dependência opcional google-antigravity."
        ) from exc
    vertex = candidate["channel"] == "vertex" or candidate["auth_mode"] in {"vertex_adc", "service_account"}
    config_kwargs: dict[str, Any] = {
        "model": candidate["model_id"],
        "system_instructions": (
            "Você é um copiloto interno do Bioma. Produza materiais rastreáveis, "
            "sem inventar fatos e sem executar escrita externa."
        ),
    }
    if vertex:
        config_kwargs.update(
            {
                "vertex": True,
                "project": settings.google_cloud_project,
                "location": settings.google_cloud_location,
            }
        )
    else:
        api_key = _env_auth_value(candidate, settings.gemini_api_key)
        if not api_key:
            raise ProviderExecutionError(
                "Credencial Gemini ausente. Configure auth_ref=env:GEMINI_API_KEY ou GEMINI_API_KEY no worker."
            )
        config_kwargs["api_key"] = api_key
    async with Agent(LocalAgentConfig(**config_kwargs)) as agent:
        response = await agent.chat(prompt)
        text = (await response.text()).strip()
        total_usage = getattr(agent.conversation, "total_usage", None)
    if not text:
        raise ProviderExecutionError("Antigravity SDK não retornou texto.")
    return {
        "text": text,
        "usage": {
            "input_units": _usage_value(total_usage, "input_tokens", "prompt_token_count"),
            "output_units": _usage_value(total_usage, "output_tokens", "candidates_token_count"),
            "cached_units": _usage_value(total_usage, "cached_tokens", "cached_content_token_count"),
        },
        "metadata": {"auth_surface": "vertex_adc" if vertex else "gemini_api_key"},
    }


def execute_antigravity_sdk(candidate: dict[str, Any], prompt: str, settings) -> dict[str, Any]:
    try:
        return asyncio.run(
            asyncio.wait_for(
                _execute_antigravity_async(candidate, prompt, settings),
                timeout=settings.ai_execution_timeout_seconds,
            )
        )
    except asyncio.TimeoutError as exc:
        raise ProviderExecutionError(
            f"Antigravity SDK excedeu o timeout de {settings.ai_execution_timeout_seconds}s."
        ) from exc


def execute_candidate(
    candidate: dict[str, Any],
    job: dict[str, Any],
    settings,
    prompt: str | None = None,
) -> dict[str, Any]:
    """Executa uma etapa na conta escolhida pelo roteamento.

    `prompt` pronto pula `build_prompt`: quem chama de fora do runner de
    workflow (o copiloto, por exemplo) já tem o texto montado com o próprio
    contrato de saída, e passar pelo template de etapa embrulharia esse texto
    dentro de outro, confundindo o modelo sobre o que deve devolver.
    """
    prompt = prompt or build_prompt(job)
    started = time.monotonic()
    if candidate["channel"] == "codex_chatgpt":
        result = execute_codex(candidate, prompt, settings)
    elif candidate["channel"] == "claude_code":
        result = execute_claude(candidate, prompt, settings)
    elif candidate["channel"] == "antigravity_cli":
        result = execute_antigravity_cli(candidate, prompt, settings)
    elif candidate["channel"] in {"antigravity_sdk", "gemini_api", "vertex"}:
        result = execute_antigravity_sdk(candidate, prompt, settings)
    elif candidate["channel"] in {"openrouter", "deepseek"}:
        result = execute_openai_compatible(candidate, prompt, settings)
    else:
        raise ProviderExecutionError(
            f"Canal {candidate['channel']} não possui executor headless seguro no worker."
        )
    result["latency_ms"] = int((time.monotonic() - started) * 1000)
    result.setdefault("currency", "USD")
    result.setdefault("cost_cents", None)
    result.setdefault("metadata", {})
    return result
