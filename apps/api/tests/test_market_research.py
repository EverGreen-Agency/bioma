from contextlib import contextmanager
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from fastapi import HTTPException

from bioma_api.schemas.market_research import (
    MarketResearchCreate,
    MarketResearchFocusOption,
    MarketResearchRefineRequest,
)
from bioma_api.services import market_research as service


WORKER_ROOT = Path(__file__).resolve().parents[2] / "worker"
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from bioma_worker.market_research import _collect_sources, _preview_report  # noqa: E402


def _payload() -> MarketResearchCreate:
    return MarketResearchCreate(
        sector="Energia solar",
        geographic_scope="Brasil",
        objective="Preparar prospecção B2B",
        selected_focus=[
            MarketResearchFocusOption(
                key="commercial_process",
                label="Processo comercial",
                description="Aquisição, qualificação e retenção.",
            )
        ],
    )


def _report(source_count: int = 3) -> dict:
    sources = [
        {
            "url": f"https://fonte{i}.example/relatorio",
            "title": f"Fonte {i}",
            "publisher": f"Publicador {i}",
            "publication_date": "2026-07-01",
            "consulted_at": "2026-07-27T12:00:00Z",
        }
        for i in range(1, source_count + 1)
    ]
    urls = [item["url"] for item in sources]
    return {
        "title": "Pesquisa de energia solar",
        "executive_summary": "Resumo com evidências.",
        "market_overview": {
            "description": "Descrição do mercado.",
            "market_size_and_segments": ["Geração distribuída"],
            "business_models": ["Venda e instalação"],
            "growth_outlook": "Perspectiva condicionada às fontes.",
            "trends": ["Armazenamento"],
            "source_urls": urls,
        },
        "commercial_process": {
            "sales_strategies": ["Venda consultiva"],
            "acquisition_and_retention": ["Indicação"],
            "buying_journey": ["Diagnóstico"],
            "qualification_signals": ["Conta de energia"],
            "source_urls": urls,
        },
        "challenges": [],
        "market_leaders": [],
        "terminology": [],
        "growth_opportunities": [],
        "prospecting_playbook": {
            "opening_angles": ["Economia e previsibilidade"],
            "qualification_questions": ["Qual é o consumo mensal?"],
            "likely_objections": ["Investimento inicial"],
            "credibility_cautions": ["Não prometer payback sem simulação."],
        },
        "content_opportunities": [],
        "caveats": [],
        "sources": sources,
    }


def test_research_provider_runs_outside_transaction_and_records_sources(eg_admin, monkeypatch):
    workspace_id = uuid4()
    tenant_id = uuid4()
    subject_id = uuid4()
    research_id = uuid4()
    open_connections = 0
    stored_sources = []

    @contextmanager
    def fake_connect():
        nonlocal open_connections
        open_connections += 1
        try:
            yield object()
        finally:
            open_connections -= 1

    def fake_generate(_request):
        assert open_connections == 0
        report = _report()
        return {
            "report": report,
            "sources": report["sources"],
            "generation_mode": "live",
            "provider": "openai",
            "model": "gpt-test",
            "response_id": "resp_test",
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            "estimated_cost_cents": None,
        }

    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(
        service,
        "resolve_accessible_client",
        lambda *_args, **_kwargs: {
            "workspace_id": workspace_id,
            "tenant_organization_id": tenant_id,
            "organization_id": subject_id,
            "access_role": "platform_admin",
            "workspace_kind": "agency_internal",
            "enabled_modules": ["hub"],
        },
    )
    monkeypatch.setattr(service.research_repo, "lock_workspace", lambda *_args: None)
    monkeypatch.setattr(service.research_repo, "next_version", lambda *_args: 1)
    monkeypatch.setattr(
        service.research_repo,
        "create_running",
        lambda *_args, **_kwargs: {"id": research_id},
    )
    monkeypatch.setattr(service, "generate_market_research_safe", fake_generate)
    monkeypatch.setattr(
        service.research_repo,
        "replace_sources",
        lambda _conn, saved_id, sources: stored_sources.extend(
            [{"research_id": saved_id, **source} for source in sources]
        ),
    )
    monkeypatch.setattr(
        service.research_repo,
        "complete_research",
        lambda *_args, **_kwargs: {"id": research_id},
    )
    monkeypatch.setattr(service, "_record_usage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service.client_hub_repo, "write_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "get_research", lambda saved_id, _user: saved_id)

    result = service.create_research(workspace_id, _payload(), eg_admin)

    assert result == research_id
    assert len(stored_sources) == 3
    assert {source["research_id"] for source in stored_sources} == {research_id}


def test_live_research_with_insufficient_sources_is_failed(eg_admin, monkeypatch):
    workspace_id = uuid4()
    research_id = uuid4()
    failed = {}

    @contextmanager
    def fake_connect():
        yield object()

    report = _report(source_count=2)
    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(
        service,
        "resolve_accessible_client",
        lambda *_args, **_kwargs: {
            "workspace_id": workspace_id,
            "tenant_organization_id": uuid4(),
            "organization_id": uuid4(),
            "access_role": "platform_admin",
            "workspace_kind": "agency_internal",
            "enabled_modules": ["hub"],
        },
    )
    monkeypatch.setattr(service.research_repo, "lock_workspace", lambda *_args: None)
    monkeypatch.setattr(service.research_repo, "next_version", lambda *_args: 1)
    monkeypatch.setattr(service.research_repo, "create_running", lambda *_args, **_kwargs: {"id": research_id})
    monkeypatch.setattr(
        service,
        "generate_market_research_safe",
        lambda _request: {
            "report": report,
            "sources": report["sources"],
            "generation_mode": "live",
            "provider": "openai",
            "model": "gpt-test",
            "response_id": "resp_test",
            "token_usage": {},
            "estimated_cost_cents": None,
        },
    )
    monkeypatch.setattr(
        service.research_repo,
        "fail_research",
        lambda _conn, saved_id, message: failed.update(id=saved_id, message=message),
    )
    monkeypatch.setattr(service.client_hub_repo, "write_audit", lambda *_args, **_kwargs: None)

    with pytest.raises(HTTPException) as exc:
        service.create_research(workspace_id, _payload(), eg_admin)

    assert exc.value.status_code == 502
    assert failed["id"] == research_id
    assert "três fontes" in failed["message"]


def test_unknown_or_hidden_research_returns_404(eg_admin, monkeypatch):
    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(service.research_repo, "find_research_context", lambda *_args: None)

    with pytest.raises(HTTPException) as exc:
        service.get_research(uuid4(), eg_admin)

    assert exc.value.status_code == 404


def test_refinement_and_generation_require_manage_work(eg_admin, monkeypatch):
    requested_capabilities = []

    @contextmanager
    def fake_connect():
        yield object()

    def reject_after_recording(_conn, _workspace_id, _user, capability):
        requested_capabilities.append(capability)
        raise HTTPException(status_code=418, detail="capability captured")

    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(service, "_workspace", reject_after_recording)

    with pytest.raises(HTTPException):
        service.refine_sector(
            uuid4(),
            MarketResearchRefineRequest(sector="Energia solar"),
            eg_admin,
        )
    with pytest.raises(HTTPException):
        service.create_research(uuid4(), _payload(), eg_admin)

    assert requested_capabilities == ["manage_work", "manage_work"]


def test_market_research_rejects_client_workspace(eg_admin, monkeypatch):
    @contextmanager
    def fake_connect():
        yield object()

    monkeypatch.setattr(service, "connect", fake_connect)
    monkeypatch.setattr(
        service,
        "resolve_accessible_client",
        lambda *_args, **_kwargs: {"workspace_kind": "client"},
    )

    with pytest.raises(HTTPException) as exc:
        service.list_researches(uuid4(), eg_admin)

    assert exc.value.status_code == 404


def test_provider_source_set_rejects_declared_url_not_seen_by_web_search():
    response = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "sources": [
                        {"type": "url", "url": "https://aneel.gov.br/fonte", "title": "ANEEL"}
                    ]
                },
            }
        ]
    }
    declared = [
        {"url": "https://aneel.gov.br/fonte", "title": "Fonte oficial", "publisher": "ANEEL"},
        {"url": "https://inventada.example/fonte", "title": "Não consultada"},
    ]

    sources = _collect_sources(response, declared)

    assert [source["url"] for source in sources] == ["https://aneel.gov.br/fonte"]
    assert sources[0]["publisher"] == "ANEEL"


def test_declared_sources_are_rejected_when_provider_returns_no_native_sources():
    sources = _collect_sources(
        {"output": []},
        [{"url": "https://inventada.example/fonte", "title": "Não consultada"}],
    )

    assert sources == []


def test_preview_report_explicitly_forbids_using_it_as_evidence():
    report = _preview_report(
        {
            "sector": "Energia solar",
            "selected_focus": [{"label": "Processo comercial"}],
        }
    )

    assert report["sources"] == []
    assert any("Nenhuma busca web" in caveat for caveat in report["caveats"])
    assert "não contém fatos" in report["executive_summary"]
