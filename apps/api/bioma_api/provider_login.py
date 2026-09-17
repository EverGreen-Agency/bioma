"""OAuth interativo dos CLIs oficiais com estado persistido e saída pública.

O Bioma não implementa OAuth de terceiros: ele abre o comando oficial em HOME
isolado, transmite URL/código para a UI e cifra os arquivos produzidos pelo CLI.
"""

from __future__ import annotations

import os
import queue
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from uuid import UUID

from bioma_api.crypto import decrypt_secret, encrypt_secret
from bioma_api.db import connect
from bioma_api.worker_bridge import pack_provider_credentials_safe


LOGIN_TIMEOUT_SECONDS = 15 * 60
LOGIN_STALE_SECONDS = 30
MAX_PUBLIC_OUTPUT = 16_000
_processes: dict[UUID, subprocess.Popen] = {}
_lock = threading.Lock()
_ansi = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_secret = re.compile(
    r'(?i)(access[_ -]?token|refresh[_ -]?token|id[_ -]?token|authorization|bearer)(["\' :=]+)([^\s"\']{16,})'
)


def _sanitize(value: str) -> str:
    clean = _ansi.sub("", value).replace("\x00", "")
    clean = _secret.sub(r"\1\2[redacted]", clean)
    return clean[-MAX_PUBLIC_OUTPUT:]


def _hide_submitted_inputs(output: str, submitted: list[str]) -> str:
    for value in submitted:
        output = output.replace(value, "[one-time code hidden]")
    return output


def _login_environment(channel: str, root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("CI", None)
    env.update({"NO_COLOR": "1", "TERM": "xterm-256color"})
    if channel == "codex_chatgpt":
        directory = root / "codex"
        directory.mkdir(parents=True)
        env["CODEX_HOME"] = str(directory)
    elif channel == "claude_code":
        directory = root / "claude"
        directory.mkdir(parents=True)
        env["CLAUDE_CONFIG_DIR"] = str(directory)
        env["BROWSER"] = "echo"
    elif channel == "antigravity_cli":
        directory = root / "home"
        directory.mkdir(parents=True)
        env["HOME"] = str(directory)
        env["XDG_CONFIG_HOME"] = str(directory / ".config")
        env["XDG_DATA_HOME"] = str(directory / ".local" / "share")
        env["SSH_CONNECTION"] = "127.0.0.1 1 127.0.0.1 22"
    return env


def _login_command(channel: str, account: dict, settings) -> list[str]:
    binary = (account.get("settings") or {}).get("binary_path")
    if channel == "codex_chatgpt":
        return [binary or settings.codex_cli_path, "login", "--device-auth"]
    if channel == "claude_code":
        return [binary or settings.claude_cli_path, "auth", "login", "--claudeai"]
    if channel == "antigravity_cli":
        return [
            binary or settings.antigravity_cli_path,
            "-p",
            "Reply exactly BIOMA_LOGIN_OK",
            "--output-format",
            "json",
            "--print-timeout",
            "15m",
        ]
    raise RuntimeError(f"Canal {channel} não suporta login interativo pelo Bioma.")


def _tty_command(command: list[str]) -> list[str]:
    script = shutil.which("script")
    if os.name != "nt" and script:
        return [script, "-qefc", shlex.join(command), "/dev/null"]
    return command


def _write_state(session_id: UUID, *, status: str | None = None, output: str | None = None,
                 prompt_hint: str | None = None, error: str | None = None) -> None:
    assignments = ["updated_at = now()"]
    values: list[object] = []
    if status:
        assignments.append("status = %s")
        values.append(status)
        if status == "running":
            assignments.append("started_at = coalesce(started_at, now())")
        if status in {"completed", "failed", "canceled", "expired"}:
            assignments.append("finished_at = now()")
    if output is not None:
        assignments.append("public_output = %s")
        values.append(_sanitize(output))
    if prompt_hint is not None:
        assignments.append("prompt_hint = %s")
        values.append(prompt_hint)
    if error is not None:
        assignments.append("error_message = %s")
        values.append(_sanitize(error)[:2000])
    values.append(session_id)
    with connect() as conn:
        conn.execute(
            f"update ai_provider_login_sessions set {', '.join(assignments)} "
            "where id = %s and status in ('pending', 'running', 'waiting_input')",
            values,
        )


def _consume_input(session_id: UUID) -> str | None:
    with connect() as conn:
        row = conn.execute(
            """
            with pending as (
              select encrypted_pending_input, status
              from ai_provider_login_sessions
              where id = %s and encrypted_pending_input is not null
                and status <> 'canceled'
              for update
            )
            update ai_provider_login_sessions session
            set encrypted_pending_input = null, updated_at = now()
            from pending
            where session.id = %s
            returning pending.encrypted_pending_input, pending.status
            """,
            (session_id, session_id),
        ).fetchone()
    if not row or row["status"] == "canceled":
        return None
    return decrypt_secret(row["encrypted_pending_input"])


def _is_stopped(session_id: UUID) -> bool:
    with connect() as conn:
        row = conn.execute("select status from ai_provider_login_sessions where id = %s", (session_id,)).fetchone()
    return not row or row["status"] not in {"pending", "running", "waiting_input"}


def _store_credentials(session_id: UUID, account: dict, root: Path, user_id: UUID) -> None:
    bundle = encrypt_secret(pack_provider_credentials_safe(root))
    auth_method = {
        "codex_chatgpt": "chatgpt_device_oauth",
        "claude_code": "claude_subscription_oauth",
        "antigravity_cli": "google_subscription_oauth",
    }[account["channel"]]
    with connect() as conn:
        conn.execute(
            """
            insert into ai_provider_credentials (
              account_id, encrypted_bundle, auth_method, created_by, updated_by
            ) values (%s, %s, %s, %s, %s)
            on conflict (account_id) do update set
              encrypted_bundle = excluded.encrypted_bundle,
              auth_method = excluded.auth_method,
              updated_by = excluded.updated_by,
              updated_at = now()
            """,
            (account["id"], bundle, auth_method, user_id, user_id),
        )
        conn.execute(
            """
            update ai_provider_accounts
            set status = 'active', auth_ref = 'vault:cli-oauth',
              health_detail = null, updated_by = %s, updated_at = now()
            where id = %s
            """,
            (user_id, account["id"]),
        )
        conn.execute(
            """
            insert into audit_logs (actor_user_id, organization_id, event_type, metadata)
            values (%s, %s, 'ai.provider_account.login_completed',
              jsonb_build_object('account_id', %s::text, 'channel', %s::text, 'session_id', %s::text))
            """,
            (user_id, account["organization_id"], str(account["id"]), account["channel"], str(session_id)),
        )


def _reader(stream, events: queue.Queue[str | None]) -> None:
    try:
        while True:
            chunk = stream.read(1)
            if not chunk:
                break
            events.put(chunk)
    finally:
        events.put(None)


def _run_login(session_id: UUID, account: dict, user_id: UUID, settings) -> None:
    root = Path(tempfile.mkdtemp(prefix=f"bioma-login-{account['channel']}-"))
    output = ""
    submitted_inputs: list[str] = []
    process: subprocess.Popen | None = None
    try:
        env = _login_environment(account["channel"], root)
        command = _tty_command(_login_command(account["channel"], account, settings))
        _write_state(session_id, status="running", prompt_hint="Abra a URL exibida e conclua o login oficial.")
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            shell=False,
            bufsize=0,
        )
        with _lock:
            _processes[session_id] = process
        if process.stdout is None or process.stdin is None:
            raise RuntimeError("Não foi possível abrir o terminal do CLI.")
        events: queue.Queue[str | None] = queue.Queue()
        threading.Thread(target=_reader, args=(process.stdout, events), daemon=True).start()
        deadline = time.monotonic() + LOGIN_TIMEOUT_SECONDS
        last_flush = 0.0
        stream_closed = False
        while process.poll() is None and time.monotonic() < deadline:
            if _is_stopped(session_id):
                process.terminate()
                return
            pending = _consume_input(session_id)
            if pending:
                submitted_inputs.append(pending.rstrip("\r\n"))
                process.stdin.write(pending.rstrip("\r\n") + "\n")
                process.stdin.flush()
            try:
                chunk = events.get(timeout=0.2)
                if chunk is None:
                    stream_closed = True
                else:
                    output += chunk
            except queue.Empty:
                pass
            now = time.monotonic()
            if now - last_flush > 0.5:
                hint = "Cole o código solicitado pelo CLI." if re.search(r"(?i)(paste|enter|cole|digite).{0,30}code|authorization code", output[-1000:]) else "Abra a URL exibida e conclua o login oficial."
                _write_state(
                    session_id,
                    status="waiting_input",
                    output=_hide_submitted_inputs(output, submitted_inputs),
                    prompt_hint=hint,
                )
                last_flush = now
            if stream_closed and process.poll() is not None:
                break
        if process.poll() is None:
            process.terminate()
            _write_state(
                session_id,
                status="expired",
                output=_hide_submitted_inputs(output, submitted_inputs),
                error="O login expirou após 15 minutos.",
            )
            return
        while not events.empty():
            chunk = events.get_nowait()
            if chunk:
                output += chunk
        if process.returncode != 0:
            raise RuntimeError(f"O CLI encerrou com código {process.returncode}.")
        if _is_stopped(session_id):
            return
        _store_credentials(session_id, account, root, user_id)
        _write_state(
            session_id,
            status="completed",
            output=_hide_submitted_inputs(output, submitted_inputs),
            prompt_hint="Login concluído e credencial cifrada.",
        )
    except Exception as exc:  # noqa: BLE001 - falha precisa virar estado consultável
        _write_state(
            session_id,
            status="failed",
            output=_hide_submitted_inputs(output, submitted_inputs),
            error=str(exc),
        )
        try:
            with connect() as conn:
                conn.execute(
                    """
                    insert into audit_logs (actor_user_id, organization_id, event_type, metadata)
                    values (%s, %s, 'ai.provider_account.login_failed',
                      jsonb_build_object('account_id', %s::text, 'channel', %s::text,
                        'session_id', %s::text, 'error', %s::text))
                    """,
                    (
                        user_id,
                        account["organization_id"],
                        str(account["id"]),
                        account["channel"],
                        str(session_id),
                        _sanitize(str(exc))[:500],
                    ),
                )
        except Exception:  # noqa: BLE001 - auditoria não pode esconder a falha original
            pass
    finally:
        with _lock:
            _processes.pop(session_id, None)
        if process and process.poll() is None:
            process.kill()
        shutil.rmtree(root, ignore_errors=True)


def start_login(session_id: UUID, account: dict, user_id: UUID, settings) -> None:
    threading.Thread(
        target=_run_login,
        args=(session_id, account, user_id, settings),
        daemon=True,
        name=f"provider-login-{session_id}",
    ).start()


def stop_login(session_id: UUID) -> None:
    with _lock:
        process = _processes.get(session_id)
    if process and process.poll() is None:
        process.terminate()
