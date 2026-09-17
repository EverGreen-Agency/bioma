from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from bioma_api.proposal_documents import render_proposal_markdown, render_proposal_pdf
from bioma_api.schemas.proposal_lifecycle import ProposalConversionCreate
from bioma_api.schemas.proposals import ProposalUpdatePayload
from bioma_api.services import proposals as proposals_service
from bioma_api.services import sales_copilot


def _proposal_document() -> dict:
    return {
        "title": "Evolução do aplicativo",
        "client_name": "Cliente exemplo",
        "contractor_name": "Evergreen Growth",
        "problem_summary": "Evoluir o produto com rastreabilidade e critérios de aceite.",
        "executive_summary": "Execução por fases, com revisão humana antes de cada marco.",
        "scope_items": [
            {"item": "Integração GitHub", "description": "Vincular entregas técnicas a issues confirmadas."},
            {"item": "Hub do cliente", "description": "Exibir andamento e critérios de aceite."},
        ],
        "team_members": ["Tech Lead", "Desenvolvedor"],
        "delivery_modality": "sprint",
        "delivery_days": 45,
        "estimated_budget": "Conforme proposta revisada",
        "payment_terms": "Conforme contrato",
        "urgency": "high",
    }


def test_canonical_proposal_document_contains_scope_without_invented_claims():
    markdown = render_proposal_markdown(_proposal_document())

    assert "# Evolução do aplicativo" in markdown
    assert "Integração GitHub" in markdown
    assert "revisão humana" in markdown
    assert "garantia de resultado" not in markdown.lower()


def test_proposal_pdf_has_valid_pdf_envelope_and_multiple_sections():
    content = render_proposal_pdf(_proposal_document())

    assert content.startswith(b"%PDF-1.4")
    assert content.rstrip().endswith(b"%%EOF")
    assert b"/Type /Catalog" in content
    assert len(content) > 1_000


def test_generic_proposal_patch_cannot_bypass_audited_status_transition(eg_admin, monkeypatch):
    def should_not_connect():
        raise AssertionError("status inválido não deve alcançar o banco")

    monkeypatch.setattr(proposals_service, "connect", should_not_connect)

    with pytest.raises(HTTPException) as exc:
        proposals_service.update_proposal(
            uuid4(),
            ProposalUpdatePayload(status="sent"),
            eg_admin,
        )

    assert exc.value.status_code == 409
    assert "transição auditada" in exc.value.detail


def test_conversion_uses_canonical_project_type():
    assert ProposalConversionCreate(
        confirm=True,
        idempotency_key="proposal-123",
        project_type="social",
    ).project_type == "social"

    with pytest.raises(ValidationError):
        ProposalConversionCreate(
            confirm=True,
            idempotency_key="proposal-123",
            project_type="social_media",
        )


def test_sales_copilot_realtime_exposes_ingestion_without_claiming_meeting_bot(eg_admin):
    adapter = sales_copilot.realtime_adapter_status(eg_admin)

    assert adapter.available is True
    assert adapter.status == "adapter_ready"
    assert adapter.transport == "polling"
    assert "ainda exige" in adapter.message
    assert "manual_transcript" in adapter.supported_input
