import base64
import json
from pathlib import Path
import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from bioma_api import crypto as api_crypto
from bioma_worker import crypto as worker_crypto
from bioma_worker.config import WorkerSettings
from bioma_api.config import Settings
from bioma_worker.provider_credentials import (
    materialize_provider_credentials,
    pack_credential_directory,
    provider_process_environment,
)


def test_roundtrip_api_encrypt_worker_decrypt(monkeypatch):
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr(api_crypto, "_fernet", lambda: Fernet(key.encode("utf-8")))

    plaintext = "super-secret-oauth-token-12345"
    encrypted = api_crypto.encrypt_secret(plaintext)
    assert encrypted.startswith("enc:v1:")

    decrypted = worker_crypto.decrypt_secret(encrypted, key)
    assert decrypted == plaintext


def test_roundtrip_worker_encrypt_api_decrypt(monkeypatch):
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr(api_crypto, "_fernet", lambda: Fernet(key.encode("utf-8")))

    plaintext = "session-bundle-payload-xyz"
    encrypted = worker_crypto.encrypt_secret(plaintext, key)
    assert encrypted.startswith("enc:v1:")

    decrypted = api_crypto.decrypt_secret(encrypted)
    assert decrypted == plaintext


def test_credential_bundle_packing_and_materialization_with_symmetric_key(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr(api_crypto, "_fernet", lambda: Fernet(key.encode("utf-8")))

    source_dir = tmp_path / "claude-home"
    claude_subdir = source_dir / "claude"
    claude_subdir.mkdir(parents=True, exist_ok=True)
    config_file = claude_subdir / "config.json"
    config_file.write_text(json.dumps({"sessionKey": "sk-ant-test"}), encoding="utf-8")

    packed_bundle = pack_credential_directory(source_dir)
    encrypted_bundle = api_crypto.encrypt_secret(packed_bundle)

    account = {
        "id": "11111111-1111-1111-1111-111111111111",
        "channel": "claude_code",
        "credential_bundle": encrypted_bundle,
    }

    materialize_root = tmp_path / "worker-materialize"
    env_vars = materialize_provider_credentials(account, key, materialization_root=materialize_root)

    assert "CLAUDE_CONFIG_DIR" in env_vars
    claude_dir = Path(env_vars["CLAUDE_CONFIG_DIR"])
    assert (claude_dir / "config.json").exists()
    assert json.loads((claude_dir / "config.json").read_text(encoding="utf-8")) == {"sessionKey": "sk-ant-test"}


def test_divergent_key_fails_cleanly():
    key_a = Fernet.generate_key().decode("utf-8")
    key_b = Fernet.generate_key().decode("utf-8")

    plaintext = "test-secret-payload"
    encrypted = worker_crypto.encrypt_secret(plaintext, key_a)

    with pytest.raises(RuntimeError, match="SECRET_ENCRYPTION_KEY trocada"):
        worker_crypto.decrypt_secret(encrypted, key_b)


def test_config_validator_accepts_valid_fernet_key():
    valid_key = Fernet.generate_key().decode("utf-8")
    worker_conf = WorkerSettings(secret_encryption_key=valid_key)
    assert worker_conf.secret_encryption_key == valid_key

    api_conf = Settings(secret_encryption_key=valid_key)
    assert api_conf.secret_encryption_key == valid_key


def test_config_validator_rejects_invalid_fernet_key():
    with pytest.raises(ValidationError):
        WorkerSettings(secret_encryption_key="not-a-valid-fernet-key")

    with pytest.raises(ValidationError):
        Settings(secret_encryption_key="not-a-valid-fernet-key")
