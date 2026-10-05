import importlib.util
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any


def _command(command: list[str], timeout: int = 15, env: dict[str, str] | None = None) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            env=env,
        )
    except FileNotFoundError:
        return False, f"Executável não encontrado: {command[0]}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout ao executar {command[0]}."
    output = (result.stdout or result.stderr or "").strip()[-2000:]
    return result.returncode == 0, output


def _env_value(account: dict[str, Any], fallback_name: str) -> bool:
    auth_ref = account.get("auth_ref")
    name = auth_ref.removeprefix("env:") if isinstance(auth_ref, str) and auth_ref.startswith("env:") else fallback_name
    return bool(os.environ.get(name))


def _module_installed(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def probe_provider_runtime(account: dict[str, Any], settings) -> dict[str, Any]:
    from bioma_worker.provider_credentials import provider_process_environment

    with provider_process_environment(account, settings) as process_env:
        return _probe_provider_runtime(account, settings, process_env)


def _probe_provider_runtime(
    account: dict[str, Any],
    settings,
    process_env: dict[str, str] | None,
) -> dict[str, Any]:
    channel = account["channel"]

    def run(command: list[str], timeout: int = 15) -> tuple[bool, str]:
        return _command(command, timeout=timeout, env=process_env) if process_env else _command(command, timeout=timeout)

    installed = False
    authenticated = False
    version: str | None = None
    auth_method: str | None = None
    quota_summary: str | None = None
    detail = "Canal sem probe implementado."
    instructions: list[str] = []

    # Resume cotas já registradas para referência no probe sem incorrer em novas chamadas
    existing_buckets = account.get("quota_buckets") or []
    if existing_buckets:
        bucket_desc = [
            f"{b.get('bucket_key')}: {b.get('remaining_percent')}% restante"
            for b in existing_buckets
            if b.get("remaining_percent") is not None
        ]
        if bucket_desc:
            quota_summary = " | ".join(bucket_desc)

    if channel == "codex_chatgpt":
        binary = (account.get("settings") or {}).get("binary_path") or settings.codex_cli_path
        installed, version_output = run([binary, "--version"])
        version = version_output or None
        if not installed:
            detail = f"Executável do Codex não encontrado: '{binary}'. Instale @openai/codex ou configure binary_path."
            instructions = [
                "Instale o CLI: npm install -g @openai/codex",
                "Verifique se o binário está no PATH do container/servidor do worker.",
                "Se estiver em caminho customizado, preencha binary_path nas configurações da conta.",
            ]
        else:
            authenticated, status_output = run([binary, "login", "status"])
            auth_method = "chatgpt_device_oauth" if authenticated else None
            if authenticated:
                detail = f"Codex instalado ({version}) e autenticado."
            else:
                detail = f"Codex instalado ({version}), mas sessão não autenticada: {status_output}"
                instructions = [
                    "Em Operações de IA, clique em Entrar com ChatGPT e conclua o device OAuth oficial.",
                    "O cofre cifrado compartilha a sessão entre API e worker via SECRET_ENCRYPTION_KEY.",
                ]

    elif channel == "claude_code":
        binary = (account.get("settings") or {}).get("binary_path") or settings.claude_cli_path
        installed, version_output = run([binary, "--version"])
        version = version_output or None
        if not installed:
            detail = f"Executável do Claude Code não encontrado: '{binary}'. Instale @anthropic-ai/claude-code ou configure binary_path."
            instructions = [
                "Instale o CLI: npm install -g @anthropic-ai/claude-code",
                "Verifique se o binário 'claude' está acessível no PATH do container do worker.",
            ]
        else:
            authenticated, status_output = run([binary, "auth", "status"])
            if authenticated:
                try:
                    status_payload = json.loads(status_output)
                    auth_method = status_payload.get("authMethod") or status_payload.get("subscriptionType")
                    if status_payload.get("loggedIn") is False:
                        authenticated = False
                        detail = "Claude Code instalado, mas status indica 'loggedIn: false'."
                    else:
                        detail = f"Claude Code instalado ({version}) e autenticado ({auth_method or 'OAuth'})."
                except json.JSONDecodeError:
                    auth_method = "claude_oauth"
                    detail = f"Claude Code instalado ({version}) e autenticado."
            else:
                detail = f"Claude Code instalado ({version}), mas não autenticado: {status_output}"
                instructions = [
                    "Em Operações de IA, clique em Entrar com Claude e conclua o OAuth oficial.",
                    "O cofre cifrado compartilha a sessão entre API e worker via SECRET_ENCRYPTION_KEY.",
                    "Para CI/servidor sem navegador, use CLAUDE_CODE_OAUTH_TOKEN configurado no ambiente.",
                ]

    elif channel == "antigravity_cli":
        binary = (account.get("settings") or {}).get("binary_path") or settings.antigravity_cli_path
        installed, version_output = run([binary, "--version"])
        version = version_output or None
        if not installed:
            detail = f"Executável do Antigravity CLI não encontrado: '{binary}'. Instale o binário agy ou configure binary_path."
            instructions = [
                "Instale o executável oficial agy no PATH do worker.",
                "Em Docker, garanta permissões de execução (chmod +x /usr/local/bin/agy).",
            ]
        else:
            # /usage consulta quotas/limites de conta sem gerar tokens nem gastar inferência
            authenticated, usage_output = run([binary, "-p", "/usage"], timeout=30)
            if authenticated:
                auth_method = "cached_google_session_or_adc"
                detail = f"Antigravity CLI instalado ({version}) e com sessão utilizável."
                # Tenta extrair resumo de cota diretamente do texto sem inferência
                usage_match = re.findall(r"(\d+(?:\.\d+)?\s*%)", usage_output)
                if usage_match and not quota_summary:
                    quota_summary = f"Cota reportada via /usage: {', '.join(usage_match[:2])} disponível"
            else:
                detail = f"Antigravity CLI instalado ({version}), mas sem sessão utilizável: {usage_output}"
                instructions = [
                    "Em Operações de IA, clique em Entrar com Google e conclua o OAuth remoto oficial.",
                    "O cofre cifrado compartilha o perfil entre API e worker via SECRET_ENCRYPTION_KEY.",
                ]

    elif channel in {"antigravity_sdk", "gemini_api"}:
        installed = _module_installed("google.antigravity")
        authenticated = _env_value(account, "GEMINI_API_KEY")
        auth_method = "gemini_api_key" if authenticated else None
        detail = "Antigravity SDK e Gemini API key disponíveis." if installed and authenticated else (
            "SDK google.antigravity ausente." if not installed else "GEMINI_API_KEY ausente no runtime."
        )
        instructions = ["Cadastre GEMINI_API_KEY como secret nos serviços API e worker."]

    elif channel == "vertex":
        installed = _module_installed("google.antigravity")
        try:
            import google.auth
            _, project = google.auth.default()
            authenticated = bool(project or settings.google_cloud_project)
        except Exception:
            authenticated = False
        auth_method = "vertex_adc" if authenticated else None
        detail = "Antigravity SDK e Vertex ADC disponíveis." if installed and authenticated else "SDK ou ADC indisponível."
        instructions = ["Configure workload identity/ADC e GOOGLE_CLOUD_PROJECT nos dois serviços."]

    elif channel == "openrouter":
        installed = True
        authenticated = _env_value(account, "OPENROUTER_API_KEY")
        auth_method = "api_key" if authenticated else None
        detail = "OPENROUTER_API_KEY disponível." if authenticated else "OPENROUTER_API_KEY ausente no runtime."
        instructions = ["Cadastre OPENROUTER_API_KEY como secret nos serviços API e worker."]

    elif channel == "deepseek":
        installed = True
        authenticated = _env_value(account, "DEEPSEEK_API_KEY")
        auth_method = "api_key" if authenticated else None
        detail = "DEEPSEEK_API_KEY disponível." if authenticated else "DEEPSEEK_API_KEY ausente no runtime."
        instructions = ["Cadastre DEEPSEEK_API_KEY como secret nos serviços API e worker."]

    elif channel == "openai_compatible":
        installed = True
        authenticated = True
        auth_method = "custom_openai_endpoint"
        detail = "Endpoint OpenAI-compatible configurado."
        instructions = ["Configure base_url e api_key nas configurações da conta se necessário."]

    else:
        from bioma_worker.free_providers import FREE_PROVIDER_PRESETS
        if channel in FREE_PROVIDER_PRESETS:
            preset = FREE_PROVIDER_PRESETS[channel]
            installed = True
            env_var = preset.get("default_env_var", "")
            has_env = _env_value(account, env_var) if env_var else False
            has_custom = bool((account.get("settings") or {}).get("api_key"))
            authenticated = has_env or has_custom or bool(account.get("has_pool_key"))
            auth_method = "api_key_or_pool" if authenticated else None
            detail = (
                f"{preset['name']} pronto para uso gratuito."
                if authenticated
                else f"Chave ausente para {preset['name']}. Cadastre no painel ou defina {env_var}."
            )
            instructions = [
                f"Cadastre uma chave gratuita no painel em 'Provedores Gratuitos & Chaves' ou configure {env_var} no .env."
            ]

    return {
        "account_id": account["id"],
        "channel": channel,
        "runtime_surface": "worker",
        "installed": installed,
        "authenticated": authenticated,
        "ready": installed and authenticated,
        "version": version,
        "auth_method": auth_method,
        "quota_summary": quota_summary,
        "detail": detail or "Sem detalhe.",
        "instructions": instructions,
        "checked_at": datetime.now(timezone.utc),
    }
