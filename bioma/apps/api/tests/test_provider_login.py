from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from bioma_api import provider_login
from bioma_api.provider_login import _hide_submitted_inputs, _is_stopped, _login_command, _sanitize, _write_state
from bioma_api.schemas.ai_routing import ProviderAccountUpdate, ProviderLoginInput
from bioma_api.services import ai_routing as service


def test_saida_publica_remove_tokens_mas_preserva_url_e_codigo():
    output = "Open https://example.test/device and enter ABCD-EFGH access_token: super-secret-token-value"

    sanitized = _sanitize(output)

    assert "https://example.test/device" in sanitized
    assert "ABCD-EFGH" in sanitized
    assert "super-secret-token-value" not in sanitized


def test_codigo_enviado_nao_volta_na_saida_publica():
    assert _hide_submitted_inputs("Code: ABCD-EFGH", ["ABCD-EFGH"]) == "Code: [one-time code hidden]"


def test_auth_ref_do_cofre_e_codigo_de_uso_unico_sao_validos():
    account = ProviderAccountUpdate(auth_ref="vault:cli-oauth")
    payload = ProviderLoginInput(value="ABCD-EFGH")

    assert account.auth_ref == "vault:cli-oauth"
    assert payload.value == "ABCD-EFGH"


def test_comandos_de_login_usam_fluxos_oficiais_e_antigravity_headless():
    settings = SimpleNamespace(codex_cli_path="codex", claude_cli_path="claude", antigravity_cli_path="agy")

    assert _login_command("codex_chatgpt", {"settings": {}}, settings) == [
        "codex", "login", "--device-auth"
    ]
    assert _login_command("claude_code", {"settings": {}}, settings) == [
        "claude", "auth", "login", "--claudeai"
    ]
    antigravity = _login_command("antigravity_cli", {"settings": {}}, settings)
    assert antigravity[:2] == ["agy", "-p"]
    assert "--output-format" in antigravity


def test_estado_terminal_bloqueia_retomada_tardia_do_processo(monkeypatch):
    session_id = uuid4()

    class FakeResult:
        def fetchone(self):
            return {"status": "failed"}

    class FakeConn:
        def __init__(self):
            self.statements = []

        def execute(self, statement, values):
            self.statements.append((statement, values))
            return FakeResult()

    conn = FakeConn()

    @contextmanager
    def fake_connect():
        yield conn

    monkeypatch.setattr(provider_login, "connect", fake_connect)

    assert _is_stopped(session_id) is True
    _write_state(session_id, status="waiting_input", output="late output")

    update_statement = conn.statements[-1][0]
    assert "status in ('pending', 'running', 'waiting_input')" in update_statement


def test_novo_login_para_mesma_conta_interrompe_o_anterior(eg_admin, monkeypatch):
    account_id = uuid4()
    new_session_id = uuid4()
    old_session_id = uuid4()
    account = {
        "id": account_id,
        "organization_id": eg_admin.organizations[0].id,
        "channel": "codex_chatgpt",
        "settings": {},
    }

    @contextmanager
    def fake_connect():
        yield object()

    stopped = []
    started = []
    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(service, "require_encryption_configured", lambda: None)
    monkeypatch.setattr(service, "ai_provider_settings_safe", lambda: SimpleNamespace())
    monkeypatch.setattr(service.repo, "get_account", lambda *_args: account)
    monkeypatch.setattr(
        service.repo,
        "create_login_session",
        lambda *_args: ({"id": new_session_id}, [old_session_id]),
    )
    monkeypatch.setattr(service.client_hub_repo, "write_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service.provider_login, "stop_login", stopped.append)
    monkeypatch.setattr(
        service.provider_login,
        "start_login",
        lambda session_id, *_args: started.append(session_id),
    )
    monkeypatch.setattr(service, "get_provider_login", lambda *_args: "session")

    result = service.start_provider_login(account_id, eg_admin)

    assert result == "session"
    assert stopped == [old_session_id]
    assert started == [new_session_id]


def test_desconectar_remove_credencial_e_audita_limite_da_revogacao(eg_admin, monkeypatch):
    account_id = uuid4()
    organization_id = eg_admin.organizations[0].id
    account = {
        "id": account_id,
        "organization_id": organization_id,
        "channel": "claude_code",
        "credential_bundle": "enc:v1:ciphertext",
    }

    @contextmanager
    def fake_connect():
        yield object()

    audits = []
    purged = []
    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(service.repo, "get_account", lambda *_args: account)
    monkeypatch.setattr(service.repo, "disconnect_provider_credentials", lambda *_args: True)
    monkeypatch.setattr(service.client_hub_repo, "write_audit", lambda *_args: audits.append(_args[4]))
    monkeypatch.setattr(service, "purge_provider_credentials_safe", purged.append)
    monkeypatch.setattr(service, "_control_plane", lambda _organization_id: "control-plane")

    result = service.disconnect_provider_credentials(account_id, eg_admin)

    assert result == "control-plane"
    assert purged == [account_id]
    assert audits == [{
        "account_id": str(account_id),
        "channel": "claude_code",
        "credential_was_configured": True,
        "upstream_revocation_required": True,
    }]
