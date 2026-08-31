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
    assert result["detail"] == "Not logged in"
