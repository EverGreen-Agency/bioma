from types import SimpleNamespace

from bioma_worker.provider_runtime import probe_provider_runtime


def _settings():
    return SimpleNamespace(
        codex_cli_path="codex",
        claude_cli_path="claude",
        antigravity_cli_path="agy",
        google_cloud_project=None,
    )


def test_antigravity_probe_confirma_sessao_pelo_usage_sem_inferencia(monkeypatch):
    commands = []

    def fake_command(command, timeout=15):
        commands.append((command, timeout))
        if command == ["agy", "--version"]:
            return True, "1.1.22"
        if command == ["agy", "-p", "/usage"]:
            return True, "Weekly Limit Remaining 72%"
        raise AssertionError(f"Comando inesperado: {command}")

    monkeypatch.setattr("bioma_worker.provider_runtime._command", fake_command)
    result = probe_provider_runtime(
        {"id": "account-1", "channel": "antigravity_cli", "settings": {}},
        _settings(),
    )

    assert result["installed"] is True
    assert result["authenticated"] is True
    assert result["ready"] is True
    assert result["version"] == "1.1.22"
    assert commands[-1] == (["agy", "-p", "/usage"], 30)


def test_codex_probe_distingue_instalacao_de_login(monkeypatch):
    def fake_command(command, timeout=15):
        if command == ["codex", "--version"]:
            return True, "codex-cli 0.150.1"
        if command == ["codex", "login", "status"]:
            return False, "Not logged in"
        raise AssertionError(f"Comando inesperado: {command}")

    monkeypatch.setattr("bioma_worker.provider_runtime._command", fake_command)
    result = probe_provider_runtime(
        {"id": "account-2", "channel": "codex_chatgpt", "settings": {}},
        _settings(),
    )

    assert result["installed"] is True
    assert result["authenticated"] is False
    assert result["ready"] is False
    assert "Not logged in" in result["detail"]


def test_claude_probe_com_status_autenticado_json(monkeypatch):
    def fake_command(command, timeout=15):
        if command == ["claude", "--version"]:
            return True, "2.1.90"
        if command == ["claude", "auth", "status"]:
            return True, '{"loggedIn": true, "authMethod": "claude_max"}'
        raise AssertionError(f"Comando inesperado: {command}")

    monkeypatch.setattr("bioma_worker.provider_runtime._command", fake_command)
    result = probe_provider_runtime(
        {"id": "account-3", "channel": "claude_code", "settings": {}},
        _settings(),
    )

    assert result["installed"] is True
    assert result["authenticated"] is True
    assert result["ready"] is True
    assert result["version"] == "2.1.90"
    assert result["auth_method"] == "claude_max"
    assert result["runtime_surface"] == "worker"


def test_claude_probe_com_sessao_expirada(monkeypatch):
    def fake_command(command, timeout=15):
        if command == ["claude", "--version"]:
            return True, "2.1.90"
        if command == ["claude", "auth", "status"]:
            return False, "Not logged in"
        raise AssertionError(f"Comando inesperado: {command}")

    monkeypatch.setattr("bioma_worker.provider_runtime._command", fake_command)
    result = probe_provider_runtime(
        {"id": "account-4", "channel": "claude_code", "settings": {}},
        _settings(),
    )

    assert result["installed"] is True
    assert result["authenticated"] is False
    assert result["ready"] is False
    assert any("Entrar com Claude" in step for step in result["instructions"])


def test_probe_extrai_resumo_de_cota_existente(monkeypatch):
    def fake_command(command, timeout=15):
        if command == ["codex", "--version"]:
            return True, "0.150.1"
        if command == ["codex", "login", "status"]:
            return True, "Logged in as test@bioma.com"
        raise AssertionError(f"Comando inesperado: {command}")

    monkeypatch.setattr("bioma_worker.provider_runtime._command", fake_command)
    result = probe_provider_runtime(
        {
            "id": "account-5",
            "channel": "codex_chatgpt",
            "settings": {},
            "quota_buckets": [
                {"bucket_key": "5_hour", "remaining_percent": 82},
                {"bucket_key": "7_day", "remaining_percent": 45},
            ],
        },
        _settings(),
    )

    assert result["quota_summary"] == "5_hour: 82% restante | 7_day: 45% restante"


def test_start_ai_execution_attempt_gera_hash_sha256():
    import hashlib
    from bioma_worker.storage import start_ai_execution_attempt

    sql_statements = []
    sql_params = []

    class FakeCursor:
        def fetchone(self):
            return {"id": "attempt-123", "attempt_number": 1, "request_hash": sql_params[0][10]}

    class FakeConn:
        def execute(self, sql, params=None):
            sql_statements.append(sql)
            sql_params.append(params)
            return FakeCursor()

    job = {
        "organization_id": "org-1",
        "run_id": "run-1",
        "step_run_id": "step-1",
        "task_kind": "social_brief",
        "prompt": "Gere um briefing clínico para Instagram",
        "workflow_input": {"topic": "Implante"},
        "previous_outputs": {},
        "step_key": "step_generate",
    }
    candidate = {
        "account_id": "acc-1",
        "model_catalog_id": "model-1",
        "score": 95,
        "reasons": ["Alta cota"],
        "quota_buckets": [],
        "policy_id": "pol-1",
        "provider": "openai",
        "model_id": "gpt-5-mini",
    }

    attempt = start_ai_execution_attempt(FakeConn(), job, candidate)

    expected_hash = hashlib.sha256("Gere um briefing clínico para Instagram".encode("utf-8")).hexdigest()
    assert len(expected_hash) == 64
    assert attempt["request_hash"] == expected_hash
    # O 11º parâmetro na tupla do INSERT (índice 10) deve ser o request_hash
    assert sql_params[0][10] == expected_hash

