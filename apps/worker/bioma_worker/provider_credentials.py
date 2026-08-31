"""Materializa credenciais cifradas de CLI sem depender de volume compartilhado.

O bundle é um JSON pequeno, cifrado no Postgres. Ele só contém arquivos criados
pelos CLIs dentro de um HOME isolado durante o login; caminhos absolutos,
symlinks e arquivos grandes são recusados na entrada e na saída.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from bioma_worker.crypto import decrypt_secret


MAX_BUNDLE_BYTES = 12 * 1024 * 1024
MAX_FILE_BYTES = 6 * 1024 * 1024


def pack_credential_directory(root: Path) -> str:
    files: list[dict[str, Any]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            raise RuntimeError(f"Arquivo de credencial excede o limite: {relative}")
        total += len(data)
        if total > MAX_BUNDLE_BYTES:
            raise RuntimeError("Bundle de credenciais excede 12 MiB.")
        files.append(
            {
                "path": relative,
                "mode": stat.S_IMODE(path.stat().st_mode),
                "content": base64.b64encode(data).decode("ascii"),
            }
        )
    if not files:
        raise RuntimeError("O CLI concluiu o login, mas não criou arquivos de credencial.")
    return json.dumps({"version": 1, "files": files}, separators=(",", ":"))


def _safe_relative_path(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeError("Bundle de credenciais contém caminho inválido.")
    return path


def materialize_provider_credentials(
    account: dict[str, Any],
    secret_encryption_key: str | None,
    materialization_root: Path | None = None,
) -> dict[str, str]:
    encrypted = account.get("credential_bundle")
    if not encrypted:
        return {}
    if not secret_encryption_key:
        raise RuntimeError("SECRET_ENCRYPTION_KEY ausente no runtime que executará o provider.")
    raw = decrypt_secret(encrypted, secret_encryption_key)
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Bundle de credenciais inválido.") from exc
    if payload.get("version") != 1 or not isinstance(payload.get("files"), list):
        raise RuntimeError("Versão de bundle de credenciais não suportada.")

    digest = hashlib.sha256(encrypted.encode("utf-8")).hexdigest()[:20]
    account_id = str(account.get("account_id") or account.get("id") or "unknown")
    root = materialization_root or Path(tempfile.gettempdir()) / "bioma-ai-credentials"
    base = root / account_id / digest
    marker = base / ".ready"
    if not marker.exists():
        parent = base.parent
        parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="materialize-", dir=parent))
        try:
            total = 0
            for item in payload["files"]:
                relative = _safe_relative_path(str(item.get("path") or ""))
                data = base64.b64decode(item.get("content") or "", validate=True)
                total += len(data)
                if len(data) > MAX_FILE_BYTES or total > MAX_BUNDLE_BYTES:
                    raise RuntimeError("Bundle de credenciais excede o limite permitido.")
                target = staging.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                os.chmod(target, int(item.get("mode") or 0o600) & 0o700)
            marker_target = staging / ".ready"
            marker_target.write_text("ok", encoding="ascii")
            try:
                staging.replace(base)
            except OSError:
                if not marker.exists():
                    raise
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    channel = account.get("channel")
    env: dict[str, str] = {}
    if channel == "codex_chatgpt":
        env["CODEX_HOME"] = str(base / "codex")
    elif channel == "claude_code":
        env["CLAUDE_CONFIG_DIR"] = str(base / "claude")
    elif channel == "antigravity_cli":
        env["HOME"] = str(base / "home")
        env.setdefault("SSH_CONNECTION", "127.0.0.1 1 127.0.0.1 22")
    return env


def purge_provider_credential_cache(account_id: Any) -> None:
    """Apaga apenas o cache efêmero de uma conta deste processo/container."""
    base = Path(tempfile.gettempdir()) / "bioma-ai-credentials" / str(account_id)
    shutil.rmtree(base, ignore_errors=True)


@contextmanager
def provider_process_environment(account: dict[str, Any], settings) -> Iterator[dict[str, str] | None]:
    """Entrega um ambiente isolado e sempre remove o material decifrado."""
    root = Path(tempfile.mkdtemp(prefix="bioma-ai-run-"))
    try:
        overrides = materialize_provider_credentials(
            account,
            getattr(settings, "secret_encryption_key", None),
            materialization_root=root,
        )
        yield {**os.environ, **overrides} if overrides else None
    finally:
        shutil.rmtree(root, ignore_errors=True)
