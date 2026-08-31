import importlib.util
import json
import os
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
    detail = "Canal sem probe implementado."
    instructions: list[str] = []

    if channel == "codex_chatgpt":
        binary = (account.get("settings") or {}).get("binary_path") or settings.codex_cli_path
        installed, version_output = run([binary, "--version"])
        version = version_output or None
        authenticated, status_output = run([binary, "login", "status"]) if installed else (False, version_output)
        auth_method = status_output or None
        detail = "Codex instalado e autenticado." if authenticated else status_output
        instructions = [
            "Em Operações de IA, clique em Entrar com ChatGPT e conclua o device OAuth oficial.",
            "O cofre cifrado compartilha a sessão entre API e worker; use a mesma SECRET_ENCRYPTION_KEY.",
            "Em automação por API, prefira OPENAI_API_KEY; access token não interativo exige workspace compatível.",
        ]
    elif channel == "claude_code":
        binary = (account.get("settings") or {}).get("binary_path") or settings.claude_cli_path
        installed, version_output = run([binary, "--version"])
        version = version_output or None
        authenticated, status_output = run([binary, "auth", "status"]) if installed else (False, version_output)
        if authenticated:
            try:
                status_payload = json.loads(status_output)
                auth_method = status_payload.get("authMethod") or status_payload.get("subscriptionType")
            except json.JSONDecodeError:
                auth_method = status_output or None
        detail = "Claude Code instalado e autenticado." if authenticated else status_output
        instructions = [
            "Em Operações de IA, clique em Entrar com Claude e conclua o OAuth oficial.",
            "O cofre cifrado compartilha a sessão entre API e worker; use a mesma SECRET_ENCRYPTION_KEY.",
            "Para CI externo ao Bioma, CLAUDE_CODE_OAUTH_TOKEN segue disponível via claude setup-token.",
        ]
    elif channel == "antigravity_cli":
        binary = (account.get("settings") or {}).get("binary_path") or settings.antigravity_cli_path
        installed, version_output = run([binary, "--version"])
        version = version_output or None
        # `/usage` consulta a conta sem gastar inferência e também prova que a
        # sessão usada depois pelo coletor de cotas está acessível.
        authenticated, models_output = run([binary, "-p", "/usage"], timeout=30) if installed else (False, version_output)
        auth_method = "cached_google_session_or_adc" if authenticated else None
        detail = "Antigravity CLI instalado e com sessão utilizável." if authenticated else models_output
        instructions = [
            "Em Operações de IA, clique em Entrar com Google e conclua o OAuth remoto oficial.",
            "O cofre cifrado compartilha o perfil entre API e worker; use a mesma SECRET_ENCRYPTION_KEY.",
            "GEMINI_API_KEY é outro canal, com cota e faturamento separados da assinatura.",
        ]
    elif channel in {"antigravity_sdk", "gemini_api"}:
        installed = _module_installed("google.antigravity")
        authenticated = _env_value(account, "GEMINI_API_KEY")
        auth_method = "gemini_api_key" if authenticated else None
        detail = "Antigravity SDK e Gemini API key disponíveis." if installed and authenticated else (
            "SDK ausente." if not installed else "GEMINI_API_KEY ausente no runtime."
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

    return {
        "account_id": account["id"],
        "channel": channel,
        "runtime_surface": "api",
        "installed": installed,
        "authenticated": authenticated,
        "ready": installed and authenticated,
        "version": version,
        "auth_method": auth_method,
        "detail": detail or "Sem detalhe.",
        "instructions": instructions,
        "checked_at": datetime.now(timezone.utc),
    }
