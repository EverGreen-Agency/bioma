"""Validações de deploy do Settings e a chave do rate limit.

As regras de `validate_deployment_settings` são a rede que impede subir
staging/produção com a configuração de cookie que a auditoria de 2026-07-12
alertou (SameSite=none sem Secure, ou origem local em produção).
"""

import pytest
from pydantic import ValidationError

from bioma_api.config import Settings


def _prod(**overrides):
    """Base válida de produção; cada teste sobrescreve o que quer quebrar."""
    base = dict(
        app_env="production",
        database_url="postgresql://bioma:bioma@db.internal:5432/bioma",
        cors_origins="https://bioma.evergreenmkt.com.br",
        session_cookie_secure=True,
    )
    base.update(overrides)
    return Settings(**base)


class TestDeploymentSafety:
    def test_producao_valida_sobe(self):
        settings = _prod()
        assert settings.cookie_secure is True

    def test_samesite_none_sem_secure_falha(self):
        # O caso exato do gap de cookie cross-site: none exige Secure.
        with pytest.raises(ValidationError):
            _prod(session_cookie_samesite="none", session_cookie_secure=False)

    def test_samesite_none_com_secure_ok(self):
        settings = _prod(session_cookie_samesite="none", session_cookie_secure=True)
        assert settings.session_cookie_samesite == "none"

    def test_producao_com_db_localhost_falha(self):
        with pytest.raises(ValidationError):
            _prod(database_url="postgresql://bioma:bioma@localhost:5432/bioma")

    def test_producao_com_cors_local_falha(self):
        with pytest.raises(ValidationError):
            _prod(cors_origins="http://localhost:5173")

    def test_producao_sem_secure_falha(self):
        with pytest.raises(ValidationError):
            _prod(session_cookie_secure=False)

    def test_ttl_zero_falha(self):
        with pytest.raises(ValidationError):
            _prod(session_ttl_hours=0)

    def test_local_e_permissivo(self):
        # Ambiente local tolera cookie inseguro e origem localhost.
        settings = Settings(app_env="local")
        assert settings.cookie_secure is False


class TestCookieSecureDefault:
    def test_local_default_inseguro(self):
        assert Settings(app_env="local").cookie_secure is False

    def test_staging_default_seguro(self):
        settings = Settings(
            app_env="staging",
            database_url="postgresql://bioma:bioma@db.internal:5432/bioma",
            cors_origins="https://staging.bioma.evergreenmkt.com.br",
        )
        assert settings.cookie_secure is True


class TestRateLimitKey:
    def test_chave_e_hash_estavel(self):
        from bioma_api.services.rate_limit import build_key

        request = type("R", (), {"client": type("C", (), {"host": "1.2.3.4"})()})()
        key1 = build_key(request, "user@example.com")
        key2 = build_key(request, "user@example.com")
        assert key1 == key2
        assert len(key1) == 64  # sha256 hex

    def test_chave_nao_contem_email_nem_ip(self):
        # LGPD: o par ip:email nunca vai em texto para o banco.
        from bioma_api.services.rate_limit import build_key

        request = type("R", (), {"client": type("C", (), {"host": "1.2.3.4"})()})()
        key = build_key(request, "user@example.com")
        assert "user@example.com" not in key
        assert "1.2.3.4" not in key

    def test_ips_diferentes_geram_chaves_diferentes(self):
        from bioma_api.services.rate_limit import build_key

        req_a = type("R", (), {"client": type("C", (), {"host": "1.1.1.1"})()})()
        req_b = type("R", (), {"client": type("C", (), {"host": "2.2.2.2"})()})()
        assert build_key(req_a, "x@y.com") != build_key(req_b, "x@y.com")

    def test_sem_client_usa_fallback(self):
        from bioma_api.services.rate_limit import build_key

        request = type("R", (), {"client": None})()
        assert len(build_key(request, "x@y.com")) == 64
