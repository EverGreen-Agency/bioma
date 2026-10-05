from types import SimpleNamespace
from unittest.mock import MagicMock
from cryptography.fernet import Fernet
import pytest

from bioma_worker.crypto import encrypt_secret
from bioma_worker.free_providers import (
    FREE_PROVIDER_PRESETS,
    execute_free_provider_call,
    get_active_provider_key,
    make_key_fingerprint,
)
from bioma_worker.storage import check_organization_budget


def test_make_key_fingerprint():
    assert make_key_fingerprint("gsk_1234567890abcdef") == "gsk_...cdef"
    assert make_key_fingerprint("curto") == "***"


def test_get_active_provider_key_from_db_pool():
    key = Fernet.generate_key().decode("ascii")
    raw_api_key = "gsk_super_secret_groq_key_12345"
    encrypted = encrypt_secret(raw_api_key, key)

    class FakeCursor:
        def fetchone(self):
            return {"id": "key-uuid-1", "key_encrypted": encrypted}

    class FakeConn:
        def execute(self, sql, params=None):
            return FakeCursor()

    api_key, key_id = get_active_provider_key(FakeConn(), "groq", key)
    assert api_key == raw_api_key
    assert key_id == "key-uuid-1"


def test_get_active_provider_key_fallback_to_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_env_groq_token")
    key = Fernet.generate_key().decode("ascii")

    class FakeEmptyCursor:
        def fetchone(self):
            return None

    class FakeConn:
        def execute(self, sql, params=None):
            return FakeEmptyCursor()

    api_key, key_id = get_active_provider_key(FakeConn(), "groq", key)
    assert api_key == "gsk_env_groq_token"
    assert key_id is None


def test_execute_free_provider_call_success(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_token")

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id": "chatcmpl-123",
                "model": "llama-3.3-70b-versatile",
                "choices": [{"message": {"role": "assistant", "content": "Olá, sou a Llama!"}}],
                "usage": {"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23},
            }

    def fake_post(url, **kwargs):
        assert "api.groq.com" in url
        assert kwargs["headers"]["Authorization"] == "Bearer gsk_test_token"
        return FakeResponse()

    monkeypatch.setattr("bioma_worker.free_providers.httpx.post", fake_post)

    settings = SimpleNamespace(secret_encryption_key=key, ai_execution_timeout_seconds=30)
    result = execute_free_provider_call(
        provider_code="groq",
        model_id="llama-3.3-70b-versatile",
        prompt="Diga olá",
        settings=settings,
        conn=None,
    )

    assert result["text"] == "Olá, sou a Llama!"
    assert result["cost_cents"] == 0
    assert result["currency"] == "USD"
    assert result["usage"] == {"input_units": 15, "output_units": 8, "cached_units": None}
    assert result["metadata"]["provider"] == "groq"


def test_execute_free_provider_call_rotates_on_429(monkeypatch):
    key = Fernet.generate_key().decode("ascii")

    calls = {"count": 0}
    db_keys = [
        {"id": "key-1", "key_encrypted": encrypt_secret("gsk_key_1", key)},
        {"id": "key-2", "key_encrypted": encrypt_secret("gsk_key_2", key)},
    ]

    class FakeConn:
        def execute(self, sql, params=None):
            class FakeCursor:
                def fetchone(self):
                    if "SELECT" in sql:
                        idx = min(calls["count"], len(db_keys) - 1)
                        return db_keys[idx]
                    return None

            return FakeCursor()

    class Fake429Response:
        status_code = 429
        text = "Rate limit exceeded"

    class Fake200Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id": "chatcmpl-456",
                "model": "llama3.1-70b",
                "choices": [{"message": {"role": "assistant", "content": "Sucesso após rotação!"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

    def fake_post(url, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return Fake429Response()
        return Fake200Response()

    monkeypatch.setattr("bioma_worker.free_providers.httpx.post", fake_post)

    settings = SimpleNamespace(secret_encryption_key=key, ai_execution_timeout_seconds=30)
    result = execute_free_provider_call(
        provider_code="cerebras",
        model_id="llama3.1-70b",
        prompt="Teste",
        settings=settings,
        conn=FakeConn(),
        max_retries=2,
    )

    assert result["text"] == "Sucesso após rotação!"
    assert calls["count"] == 2


def test_check_organization_budget_hard_stop():
    class FakeConn:
        def __init__(self, budget, usage):
            self._budget = budget
            self._usage = usage

        def execute(self, sql, params=None):
            class FakeCursor:
                def __init__(self, data):
                    self._data = data

                def fetchone(self):
                    return self._data

            if "ai_organization_budgets" in sql:
                return FakeCursor(self._budget)
            if "ai_execution_attempts" in sql:
                return FakeCursor(self._usage)
            return FakeCursor(None)

    # Caso 1: Dentro do orçamento
    conn_ok = FakeConn(
        budget={"monthly_token_cap": 10000, "monthly_cost_cap_cents": 500, "alert_threshold_percent": 80, "enforce_hard_stop": True},
        usage={"tokens_used": 5000, "cost_cents_used": 200},
    )
    status_ok = check_organization_budget(conn_ok, "org-uuid")
    assert status_ok["allowed"] is True
    assert status_ok["tokens_used"] == 5000

    # Caso 2: Estouro de tokens com hard-stop ativado
    conn_blocked = FakeConn(
        budget={"monthly_token_cap": 10000, "monthly_cost_cap_cents": 500, "alert_threshold_percent": 80, "enforce_hard_stop": True},
        usage={"tokens_used": 10500, "cost_cents_used": 200},
    )
    status_blocked = check_organization_budget(conn_blocked, "org-uuid")
    assert status_blocked["allowed"] is False
    assert "Teto de tokens atingido" in status_blocked["reason"]
