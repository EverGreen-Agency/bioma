import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


class QuotaCollectionError(RuntimeError):
    pass


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _epoch_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def parse_claude_rate_limits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normaliza o contrato oficial entregue ao status line do Claude Code."""
    rate_limits = payload.get("rate_limits")
    if not isinstance(rate_limits, dict):
        raise QuotaCollectionError(
            "Claude Code não entregou rate_limits; o campo só aparece para assinantes após uma resposta."
        )
    measured_at = datetime.now(timezone.utc)
    buckets: list[dict[str, Any]] = []
    for key, duration in (("five_hour", 300), ("seven_day", 10080)):
        window = rate_limits.get(key)
        if not isinstance(window, dict) or window.get("used_percentage") is None:
            continue
        used = Decimal(str(window["used_percentage"]))
        buckets.append(
            {
                "bucket_key": f"claude:{key.replace('_', '-')}",
                "scope": "account",
                "model_id": None,
                "total_units": None,
                "used_units": None,
                "used_percent": used,
                "remaining_percent": Decimal("100") - used,
                "unit": "percent",
                "window_duration_minutes": duration,
                "resets_at": _epoch_to_datetime(window.get("resets_at")),
                "source": "provider_cli",
                "confidence": "authoritative",
                "measured_at": measured_at,
                "raw_metadata": {"window": key, "statusline_version": payload.get("version")},
                "notes": "Campos rate_limits oficiais do status line do Claude Code após uma resposta mínima.",
            }
        )
    if not buckets:
        raise QuotaCollectionError("Claude Code respondeu sem janelas de cinco horas ou sete dias.")
    return buckets


def collect_claude_rate_limits(
    binary: str,
    timeout_seconds: int = 90,
    env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Executa uma resposta mínima e captura o JSON documentado do status line.

    `rate_limits` só existe depois da primeira resposta da sessão. O coletor
    gasta uma quantidade pequena da própria cota para obter um snapshot atual;
    isso é registrado na nota do bucket e nunca é disfarçado como leitura grátis.
    """
    with tempfile.TemporaryDirectory(prefix="bioma-claude-quota-") as directory:
        root = Path(directory)
        capture = root / "statusline.json"
        writer = root / "capture_statusline.py"
        writer.write_text(
            "import pathlib, sys\n"
            f"pathlib.Path({str(capture)!r}).write_text(sys.stdin.read(), encoding='utf-8')\n",
            encoding="utf-8",
        )
        os.chmod(writer, 0o700)
        command = f'python "{writer}"'
        settings = json.dumps(
            {"statusLine": {"type": "command", "command": command, "padding": 0}},
            separators=(",", ":"),
        )
        try:
            result = subprocess.run(
                [
                    binary,
                    "-p",
                    "Reply exactly BIOMA_QUOTA_OK",
                    "--output-format",
                    "json",
                    "--tools",
                    "",
                    "--no-session-persistence",
                    "--settings",
                    settings,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                env=env,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise QuotaCollectionError(f"Executável Claude não encontrado: {binary}") from exc
        except subprocess.TimeoutExpired as exc:
            raise QuotaCollectionError("Timeout ao consultar limites do Claude Code.") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "falha sem detalhe").strip()[-2000:]
            raise QuotaCollectionError(f"Claude Code recusou a coleta: {detail}")
        deadline = time.monotonic() + 3
        while not capture.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not capture.exists():
            raise QuotaCollectionError(
                "Claude Code concluiu a resposta, mas o status line não entregou o snapshot de cota."
            )
        try:
            payload = json.loads(capture.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QuotaCollectionError("Status line do Claude Code retornou JSON inválido.") from exc
        return parse_claude_rate_limits(payload)


def parse_codex_rate_limits(result: dict[str, Any]) -> list[dict[str, Any]]:
    buckets: list[dict[str, Any]] = []
    snapshots: list[tuple[str, dict[str, Any]]] = []
    if isinstance(result.get("rateLimits"), dict):
        snapshots.append(("default", result["rateLimits"]))
    for limit_id, snapshot in (result.get("rateLimitsByLimitId") or {}).items():
        if isinstance(snapshot, dict):
            snapshots.append((str(limit_id), snapshot))
    measured_at = datetime.now(timezone.utc)
    seen: set[tuple[str, str, int | None]] = set()
    for limit_id, snapshot in snapshots:
        for window_name in ("primary", "secondary"):
            window = snapshot.get(window_name)
            if not isinstance(window, dict):
                continue
            duration = window.get("windowDurationMins")
            dedupe_key = (limit_id, window_name, duration)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            used = Decimal(str(window["usedPercent"])) if window.get("usedPercent") is not None else None
            buckets.append(
                {
                    "bucket_key": f"codex:{limit_id}:{window_name}",
                    "scope": "model_family" if limit_id != "default" else "account",
                    "model_id": None if limit_id == "default" else limit_id,
                    "total_units": None,
                    "used_units": None,
                    "used_percent": used,
                    "remaining_percent": Decimal("100") - used if used is not None else None,
                    "unit": "percent",
                    "window_duration_minutes": duration,
                    "resets_at": _epoch_to_datetime(window.get("resetsAt")),
                    "source": "provider_api",
                    "confidence": "authoritative",
                    "measured_at": measured_at,
                    "raw_metadata": {
                        "limit_id": limit_id,
                        "window": window_name,
                        "plan_type": snapshot.get("planType"),
                        "rate_limit_reached_type": snapshot.get("rateLimitReachedType"),
                    },
                    "notes": "Coletado do contrato estável account/rateLimits/read do Codex App Server.",
                }
            )
    reset_credits = result.get("rateLimitResetCredits")
    if isinstance(reset_credits, dict) and reset_credits.get("availableCount") is not None:
        buckets.append(
            {
                "bucket_key": "codex:rate-limit-reset-credits",
                "scope": "credits",
                "model_id": None,
                "total_units": Decimal(str(reset_credits["availableCount"])),
                "used_units": Decimal("0"),
                "used_percent": None,
                "remaining_percent": None,
                "unit": "resets",
                "window_duration_minutes": None,
                "resets_at": None,
                "source": "provider_api",
                "confidence": "authoritative",
                "measured_at": measured_at,
                "raw_metadata": {"credits": reset_credits.get("credits")},
                "notes": "availableCount é o total autoritativo; a lista de créditos pode ser limitada pelo backend.",
            }
        )
    if not buckets:
        raise QuotaCollectionError("Codex App Server respondeu sem janelas de cota disponíveis.")
    return buckets


def _reader(stream, output: queue.Queue) -> None:
    try:
        for line in iter(stream.readline, ""):
            if not line:
                break
            try:
                output.put(json.loads(line))
            except json.JSONDecodeError:
                continue
    finally:
        output.put(None)


def _response_for(output: queue.Queue, request_id: int, timeout_seconds: int) -> dict[str, Any]:
    while True:
        try:
            message = output.get(timeout=timeout_seconds)
        except queue.Empty as exc:
            raise QuotaCollectionError("Timeout aguardando resposta do Codex App Server.") from exc
        if message is None:
            raise QuotaCollectionError("Codex App Server encerrou antes de responder.")
        if message.get("id") != request_id:
            continue
        if message.get("error"):
            error = message["error"]
            raise QuotaCollectionError(f"Codex App Server recusou a coleta: {error.get('message', error)}")
        return message.get("result") or {}


def collect_codex_rate_limits(
    binary: str, timeout_seconds: int = 30, env: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    try:
        process = subprocess.Popen(
            [binary, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise QuotaCollectionError(f"Executável Codex não encontrado: {binary}") from exc
    if process.stdin is None or process.stdout is None:
        process.kill()
        raise QuotaCollectionError("Não foi possível abrir o transporte stdio do Codex App Server.")
    messages: queue.Queue = queue.Queue()
    threading.Thread(target=_reader, args=(process.stdout, messages), daemon=True).start()

    def send(message: dict[str, Any]) -> None:
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()

    try:
        send(
            {
                "method": "initialize",
                "id": 1,
                "params": {
                    "clientInfo": {
                        "name": "bioma_ai_control_plane",
                        "title": "Bioma AI Control Plane",
                        "version": "0.1.0",
                    }
                },
            }
        )
        _response_for(messages, 1, timeout_seconds)
        send({"method": "initialized", "params": {}})
        send({"method": "account/rateLimits/read", "id": 2})
        result = _response_for(messages, 2, timeout_seconds)
        return parse_codex_rate_limits(result)
    finally:
        try:
            process.stdin.close()
        except OSError:
            pass
        try:
            process.terminate()
            process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()


def parse_antigravity_usage(raw: str) -> list[dict[str, Any]]:
    """Normaliza o relatório textual oficial de `agy -p /usage`.

    O CLI ainda não oferece um envelope JSON para slash commands. Mantemos o
    texto bruto na evidência e só marcamos como medido aquilo que aparece como
    percentual explícito; reset exato fica vazio em vez de ser inventado.
    """
    clean = ANSI_ESCAPE.sub("", raw).replace("\r", "")
    measured_at = datetime.now(timezone.utc)
    buckets: list[dict[str, Any]] = []
    current_group = "all-models"
    for raw_line in clean.splitlines():
        line = raw_line.strip().strip("│").strip()
        if not line:
            continue
        lowered = line.lower()
        if "model" in lowered and not re.search(r"\d+(?:\.\d+)?\s*%", line):
            current_group = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or current_group
        match = re.search(
            r"(?P<label>(?:five|5)[ -]?hour|weekly)[^0-9]*(?P<remaining>\d+(?:\.\d+)?)\s*%",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        label = match.group("label").lower()
        weekly = "week" in label
        duration = 10080 if weekly else 300
        window = "weekly" if weekly else "five-hour"
        remaining = Decimal(match.group("remaining"))
        buckets.append(
            {
                "bucket_key": f"antigravity:{current_group}:{window}",
                "scope": "model_family",
                "model_id": None,
                "total_units": None,
                "used_units": None,
                "used_percent": Decimal("100") - remaining,
                "remaining_percent": remaining,
                "unit": "percent",
                "window_duration_minutes": duration,
                "resets_at": None,
                "source": "provider_cli",
                "confidence": "measured",
                "measured_at": measured_at,
                "raw_metadata": {"group": current_group, "line": line, "report": clean[-12000:]},
                "notes": (
                    "Percentual lido do relatório /usage do Antigravity CLI; "
                    "o CLI não expôs instante de reset estruturado."
                ),
            }
        )
    if not buckets:
        raise QuotaCollectionError(
            "Antigravity CLI respondeu sem percentuais reconhecíveis para as janelas semanal e de cinco horas."
        )
    return buckets


def collect_antigravity_usage(
    binary: str, timeout_seconds: int = 30, env: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            [binary, "-p", "/usage"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise QuotaCollectionError(f"Executável Antigravity não encontrado: {binary}") from exc
    except subprocess.TimeoutExpired as exc:
        raise QuotaCollectionError("Timeout ao consultar /usage do Antigravity CLI.") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "falha sem detalhe").strip()[-2000:]
        raise QuotaCollectionError(f"Antigravity CLI recusou a coleta: {detail}")
    return parse_antigravity_usage(result.stdout)
