from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from bioma_api.repositories import proposals as proposals_repo
from bioma_api.schemas.proposals import ProposalBriefCreatePayload, ProposalCreatePayload
from bioma_api.services import proposals as proposals_service


@contextmanager
def _connection():
    yield object()


def test_proposals_backoffice_rejects_client_user_before_database(client_user_factory, monkeypatch):
    def should_not_connect():
        raise AssertionError("usuário sem permissão não pode alcançar o banco")

    monkeypatch.setattr(proposals_service, "connect", should_not_connect)

    with pytest.raises(HTTPException) as exc:
        proposals_service.list_opportunities(client_user_factory())

    assert exc.value.status_code == 403


def test_proposal_generation_consumes_all_three_pillars(eg_admin, monkeypatch):
    opportunity_id = uuid4()
    proposal_id = uuid4()
    now = datetime.now(timezone.utc)
    opportunity = {
        "id": opportunity_id,
        "title": "Aplicativo veterinário com portal do cliente",
        "description": "Evolução de produto React e FastAPI",
        "budget_text": None,
        "source_platform": "manual",
    }
    saved_payload = {}
    called_pillars = []
    commercial_activities = []

    outputs = {
        "oferta": {"headline": "Evolução do aplicativo", "mecanismo_unico": "Escopo por fases"},
        "conversao": {
            "script_fechamento": "Validar escopo e critérios de aceite.",
            "sequencia_whatsapp": [],
            "quebra_objecoes": {"esta_caro": "", "preciso_pensar": ""},
        },
        "demanda": {
            "estrutura_campanha": "Não aplicável ao projeto Tech.",
            "publicos_alvo": [],
            "variacoes_ads": [],
            "orcamento_sugerido_diario_cents": 0,
        },
    }

    def fake_execute(*, pilar, **_kwargs):
        called_pillars.append(pilar)
        return {
            "output_data": outputs[pilar],
            "generation_mode": "live",
            "token_usage": {},
            "estimated_cost_cents": 1,
            "execution_logs": [],
            "completed_at": now.isoformat(),
        }

    def fake_create(_conn, payload, user_id):
        saved_payload.update(payload)
        return {
            **payload,
            "id": proposal_id,
            "public_token": "public-token",
            "public_expires_at": now + timedelta(days=30),
            "created_by_user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }

    monkeypatch.setattr(proposals_service, "connect", _connection)
    monkeypatch.setattr(proposals_service, "execute_squad_pipeline_safe", fake_execute)
    monkeypatch.setattr(proposals_repo, "get_opportunity", lambda _conn, _id: opportunity)
    monkeypatch.setattr(proposals_repo, "create_proposal", fake_create)
    monkeypatch.setattr(proposals_repo, "update_opportunity_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        proposals_repo,
        "create_commercial_activity",
        lambda _conn, _opportunity_id, payload, _user_id: commercial_activities.append(payload),
    )

    proposal = proposals_service.generate_proposal_for_opportunity(opportunity_id, eg_admin)

    assert called_pillars == ["oferta", "conversao", "demanda"]
    assert proposal.executive_summary == outputs["oferta"]["headline"]
    assert proposal.scope_conversion == outputs["conversao"]["script_fechamento"]
    assert proposal.scope_demand == outputs["demanda"]["estrutura_campanha"]
    assert proposal.pricing_cents == 0
    assert proposal.delivery_days == 0
    assert proposal.generation_mode == "live"
    assert saved_payload["attached_cases"] == []
    assert commercial_activities[0]["activity_type"] == "proposal_created"


def test_proposal_analytics_only_counts_decisions_and_never_invents_roi(monkeypatch):
    monkeypatch.setattr(
        proposals_repo,
        "list_proposals",
        lambda _conn, limit=500: [
            {"status": "won", "pricing_cents": 100_000, "source_platform": "manual"},
            {"status": "lost", "pricing_cents": 50_000, "source_platform": "manual"},
            {"status": "sent", "pricing_cents": 75_000, "source_platform": "manual"},
        ],
    )
    monkeypatch.setattr(proposals_repo, "list_platform_configs", lambda _conn: [])

    metrics = proposals_repo.get_proposal_analytics_metrics(object())

    assert metrics["win_rate_percentage"] == 50.0
    assert metrics["overall_roi_percentage"] == 0.0
    assert metrics["platform_performance"][0]["cac_cents"] == 0


def test_manual_proposal_is_not_labeled_as_live():
    payload = ProposalCreatePayload(
        client_name="Cliente",
        target_niche="Tech",
        executive_summary="Escopo sujeito a validação humana.",
    )

    assert payload.generation_mode == "manual"


def test_proposal_brief_rejects_unknown_service():
    with pytest.raises(ValueError):
        ProposalBriefCreatePayload(
            workspace_id=uuid4(),
            title="Evolução do aplicativo",
            proposal_type="project",
            contractor_name="Evergreen",
            delivery_modality="project",
            selected_services=["servico_inventado"],
            estimated_budget="R$ 20.000",
            payment_terms="50% no início e 50% na entrega",
            urgency="high",
            decision_maker="Diretoria",
            problem_summary="Evoluir o produto com escopo e critérios de aceite claros.",
        )


def test_generate_proposal_from_brief_links_canonical_workspace(eg_admin, monkeypatch):
    workspace_id = uuid4()
    proposal_id = uuid4()
    now = datetime.now(timezone.utc)
    saved_payload = {}
    payload = ProposalBriefCreatePayload(
        workspace_id=workspace_id,
        title="Fase 3 do aplicativo",
        proposal_type="project",
        contractor_name="Evergreen",
        team_members=["Tech Lead", "Desenvolvedor"],
        delivery_modality="sprint",
        selected_services=["software_development", "systems_integration"],
        estimated_budget="A definir após validação do escopo",
        payment_terms="Conforme contrato",
        urgency="high",
        decision_maker="Diretoria da cliente",
        problem_summary="Concluir a segunda evolução do aplicativo com rastreabilidade.",
    )
    outputs = {
        "oferta": {"headline": "Evolução rastreável", "mecanismo_unico": "Entrega por fases"},
        "conversao": {"script_fechamento": "Validar escopo.", "sequencia_whatsapp": []},
        "demanda": {"estrutura_campanha": "Não aplicável.", "publicos_alvo": []},
    }

    def fake_execute(*, pilar, **_kwargs):
        return {
            "output_data": outputs[pilar],
            "generation_mode": "preview",
            "token_usage": {},
            "estimated_cost_cents": 0,
            "execution_logs": [],
            "completed_at": now.isoformat(),
        }

    def fake_create(_conn, data, user_id):
        saved_payload.update(data)
        return {
            **data,
            "series_id": uuid4(),
            "version": 1,
            "id": proposal_id,
            "public_token": "public-token",
            "public_expires_at": now + timedelta(days=30),
            "created_by_user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }

    monkeypatch.setattr(proposals_service, "connect", _connection)
    monkeypatch.setattr(proposals_service, "execute_squad_pipeline_safe", fake_execute)
    monkeypatch.setattr(
        proposals_repo,
        "get_workspace_proposal_context",
        lambda _conn, _id: {
            "workspace_id": workspace_id,
            "workspace_name": "Univet",
            "workspace_slug": "univet",
            "tenant_organization_id": uuid4(),
            "subject_organization_id": uuid4(),
            "organization_name": "Univet",
            "sector": "Saúde veterinária",
            "primary_offer": "Aplicativo",
        },
    )
    monkeypatch.setattr(proposals_repo, "create_proposal", fake_create)

    proposal = proposals_service.generate_proposal_from_brief(payload, eg_admin)

    assert proposal.workspace_id == workspace_id
    assert proposal.client_name == "Univet"
    assert proposal.generation_mode == "preview"
    assert saved_payload["intake_snapshot"]["schema_key"] == "commercial_proposal_v1"
    assert saved_payload["selected_services"] == ["software_development", "systems_integration"]
    assert saved_payload["scope_items"][0]["service_key"] == "software_development"
