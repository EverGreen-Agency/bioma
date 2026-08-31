import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from bioma_worker.ai_providers import (
    execute_openai_compatible,
    parse_antigravity_json,
    parse_claude_json,
    parse_codex_jsonl,
)
from bioma_worker.ai_routing import rank_candidates
from bioma_worker.quota_collectors import (
    parse_antigravity_usage,
    parse_claude_rate_limits,
    parse_codex_rate_limits,
)


def test_codex_quota_parser_preserva_janelas_e_reset_credit():
    buckets = parse_codex_rate_limits(
        {
            "rateLimits": {
                "primary": {"usedPercent": 25, "windowDurationMins": 300, "resetsAt": 1785000000},
                "secondary": {"usedPercent": 60, "windowDurationMins": 10080, "resetsAt": 1785600000},
                "planType": "pro",
            },
            "rateLimitResetCredits": {"availableCount": 2, "credits": []},
        }
    )
    assert [(bucket["window_duration_minutes"], bucket["remaining_percent"]) for bucket in buckets[:2]] == [
        (300, 75),
        (10080, 40),
    ]
    assert buckets[2]["total_units"] == 2
    assert buckets[2]["remaining_percent"] is None


def test_codex_exec_parser_le_mensagem_e_tokens():
    raw = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "thr_1"}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Entrega"}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5, "cached_input_tokens": 2}}),
        ]
    )
    result = parse_codex_jsonl(raw)
    assert result["text"] == "Entrega"
    assert result["external_event_id"] == "thr_1"
    assert result["usage"] == {"input_units": 10, "output_units": 5, "cached_units": 2}


def test_claude_parser_nao_inventa_custo_e_converte_quando_fornecido():
    result = parse_claude_json(
        json.dumps(
            {
                "result": "Roteiro",
                "session_id": "claude_1",
                "usage": {"input_tokens": 20, "output_tokens": 8},
                "total_cost_usd": 0.123,
            }
        )
    )
    assert result["text"] == "Roteiro"
    assert result["cost_cents"] == 12


def test_claude_quota_parser_preserva_janelas_e_reset_oficiais():
    buckets = parse_claude_rate_limits(
        {
            "version": "2.1.90",
            "rate_limits": {
                "five_hour": {"used_percentage": 23.5, "resets_at": 1785000000},
                "seven_day": {"used_percentage": 41.2, "resets_at": 1785600000},
            },
        }
    )

    assert [(bucket["window_duration_minutes"], bucket["remaining_percent"]) for bucket in buckets] == [
        (300, Decimal("76.5")),
        (10080, Decimal("58.8")),
    ]
    assert all(bucket["confidence"] == "authoritative" for bucket in buckets)
    assert all(bucket["resets_at"] is not None for bucket in buckets)


def test_antigravity_exec_parser_preserva_uso_e_conversa():
    result = parse_antigravity_json(
        json.dumps(
            {
                "status": "SUCCESS",
                "response": "Plano",
                "conversation_id": "agy_1",
                "num_turns": 1,
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "thinking_tokens": 8,
                    "cache_read_tokens": 30,
                },
            }
        )
    )
    assert result["text"] == "Plano"
    assert result["external_event_id"] == "agy_1"
    assert result["usage"] == {"input_units": 100, "output_units": 20, "cached_units": 30}


def test_antigravity_quota_parser_separa_semana_e_cinco_horas():
    buckets = parse_antigravity_usage(
        """
        Gemini Models
        Weekly Limit Remaining 72%
        Five Hour Limit Remaining 31%
        Claude and GPT models
        Weekly Limit Remaining 55%
        Five Hour Limit Remaining 80%
        """
    )
    assert [(bucket["window_duration_minutes"], bucket["remaining_percent"]) for bucket in buckets] == [
        (10080, 72),
        (300, 31),
        (10080, 55),
        (300, 80),
    ]


def _api_settings(**overrides):
    values = {
        "openrouter_api_key": "or-key",
        "openrouter_base_url": "https://openrouter.test/api/v1",
        "openrouter_site_url": "https://bioma.test",
        "openrouter_app_name": "Bioma",
        "deepseek_api_key": "ds-key",
        "deepseek_base_url": "https://deepseek.test",
        "ai_execution_timeout_seconds": 60,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_openrouter_executor_preserva_modelo_uso_e_custo(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return _FakeResponse(
            {
                "id": "generation-1",
                "model": "anthropic/claude-sonnet-4.6",
                "choices": [{"message": {"content": "Material pronto"}}],
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 30,
                    "cost": 0.042,
                    "prompt_tokens_details": {"cached_tokens": 40},
                },
            }
        )

    monkeypatch.setattr("bioma_worker.ai_providers.httpx.post", fake_post)
    result = execute_openai_compatible(
        {
            "channel": "openrouter",
            "model_id": "anthropic/claude-sonnet-4.6",
            "auth_ref": None,
        },
        "Crie um roteiro",
        _api_settings(),
    )

    assert captured["url"] == "https://openrouter.test/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer or-key"
    assert result["text"] == "Material pronto"
    assert result["usage"] == {"input_units": 120, "output_units": 30, "cached_units": 40}
    assert result["cost_cents"] == 4
    assert result["metadata"]["served_model"] == "anthropic/claude-sonnet-4.6"


def test_deepseek_executor_ativa_thinking_para_modelo_de_reasoning(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return _FakeResponse(
            {
                "id": "chat-1",
                "model": "deepseek-v4-pro",
                "choices": [{"message": {"content": "Análise"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
        )

    monkeypatch.setattr("bioma_worker.ai_providers.httpx.post", fake_post)
    result = execute_openai_compatible(
        {
            "channel": "deepseek",
            "model_id": "deepseek-v4-pro",
            "model_capabilities": ["reasoning"],
            "auth_ref": None,
        },
        "Analise",
        _api_settings(),
    )

    assert captured["url"] == "https://deepseek.test/chat/completions"
    assert captured["json"]["thinking"] == {"type": "enabled"}
    assert result["text"] == "Análise"


def _candidate(**overrides):
    row = {
        "account_id": "a",
        "provider": "openai",
        "channel": "codex_chatgpt",
        "account_name": "Codex",
        "auth_mode": "chatgpt",
        "execution_mode": "local_cli",
        "auth_ref": None,
        "account_status": "active",
        "account_capabilities": ["content"],
        "account_settings": {},
        "model_catalog_id": "m",
        "model_id": "model",
        "model_name": "Model",
        "capability_tier": "balanced",
        "model_capabilities": ["content"],
        "quality_score": 90,
        "cost_score": 80,
        "latency_score": 70,
        "priority": 10,
        "policy_id": None,
        "allowed_channels": [],
        "allowed_models": [],
        "preferred_tiers": ["balanced"],
        "quality_weight": 35,
        "quota_weight": 25,
        "cost_weight": 20,
        "reliability_weight": 10,
        "latency_weight": 10,
        "minimum_quota_headroom": 10,
        "requires_human_approval": True,
        "allow_fallback": True,
        "quota_buckets": [],
    }
    row.update(overrides)
    return row


def test_router_bloqueia_cota_baixa_e_handoff_manual():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    low_quota = _candidate(
        quota_buckets=[{"remaining_percent": 5, "resets_at": future, "confidence": "authoritative", "model_id": None}]
    )
    antigravity_cli = _candidate(
        account_id="g",
        model_catalog_id="gm",
        channel="antigravity_cli",
        execution_mode="manual_handoff",
    )
    ranked = rank_candidates({"capability": "content"}, [low_quota, antigravity_cli])
    assert all(not candidate["eligible"] for candidate in ranked)
    assert any("cota abaixo" in reason for reason in ranked[0]["reasons"] + ranked[1]["reasons"])
    assert any("handoff manual" in reason for reason in ranked[0]["reasons"] + ranked[1]["reasons"])


def test_router_prioriza_modelo_escolhido_no_harness_sem_remover_fallback():
    preferred = _candidate(model_id="preferred", role_preferred=True, quality_score=80)
    fallback = _candidate(model_catalog_id="m2", model_id="fallback", quality_score=85)
    ranked = rank_candidates({"capability": "content"}, [fallback, preferred])
    assert ranked[0]["model_id"] == "preferred"
    assert all(candidate["eligible"] for candidate in ranked)
