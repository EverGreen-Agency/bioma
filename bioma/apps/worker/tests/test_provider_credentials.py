import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from bioma_worker.crypto import encrypt_secret
from bioma_worker.provider_credentials import (
    materialize_provider_credentials,
    pack_credential_directory,
    provider_process_environment,
)


def test_bundle_cifrado_materializa_codex_home(tmp_path: Path):
    source = tmp_path / "source"
    auth = source / "codex" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text('{"tokens":"secret"}', encoding="utf-8")
    key = Fernet.generate_key().decode("ascii")
    encrypted = encrypt_secret(pack_credential_directory(source), key)

    env = materialize_provider_credentials(
        {"account_id": "test-account", "channel": "codex_chatgpt", "credential_bundle": encrypted},
        key,
        materialization_root=tmp_path / "materialized",
    )

    assert Path(env["CODEX_HOME"], "auth.json").read_text(encoding="utf-8") == '{"tokens":"secret"}'


def test_materializador_recusa_path_traversal():
    key = Fernet.generate_key().decode("ascii")
    payload = json.dumps({"version": 1, "files": [{"path": "../escape", "content": "eA==", "mode": 384}]})
    encrypted = encrypt_secret(payload, key)

    with pytest.raises(RuntimeError, match="caminho inválido"):
        materialize_provider_credentials(
            {"account_id": "invalid", "channel": "claude_code", "credential_bundle": encrypted},
            key,
        )


def test_bundle_exige_mesma_chave_de_cifra(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "credential").write_text("secret", encoding="utf-8")
    encrypted = encrypt_secret(pack_credential_directory(source), Fernet.generate_key().decode("ascii"))

    with pytest.raises(Exception):
        materialize_provider_credentials(
            {"account_id": "wrong-key", "channel": "antigravity_cli", "credential_bundle": encrypted},
            Fernet.generate_key().decode("ascii"),
        )


def test_ambiente_do_provider_apaga_material_decifrado_ao_sair(tmp_path: Path):
    source = tmp_path / "source"
    auth = source / "claude" / ".credentials.json"
    auth.parent.mkdir(parents=True)
    auth.write_text('{"oauth":"secret"}', encoding="utf-8")
    key = Fernet.generate_key().decode("ascii")
    encrypted = encrypt_secret(pack_credential_directory(source), key)
    account = {"account_id": "ephemeral", "channel": "claude_code", "credential_bundle": encrypted}

    with provider_process_environment(account, SimpleNamespace(secret_encryption_key=key)) as env:
        credential_path = Path(env["CLAUDE_CONFIG_DIR"], ".credentials.json")
        materialization_root = credential_path.parents[3]
        assert credential_path.read_text(encoding="utf-8") == '{"oauth":"secret"}'
        assert materialization_root.exists()

    assert not materialization_root.exists()
