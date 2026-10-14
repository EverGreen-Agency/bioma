"""Classificador de leads (`bioma_api.lead_classifier`).

Fixam o contrato que protege o CRM do cliente: o classificador só escolhe opção que
existe no campo, só grava campo vazio, e o estado vem do DDD, não de palpite.
"""

from bioma_api.kommo_insights import DIMENSIONS
from bioma_api.lead_classifier import (
    UNDECIDED,
    build_questions,
    build_state,
    classify_with_rules,
    decisions_from_answers,
    field_specs,
    merge_decisions,
    payload_for_kommo,
    uf_from_phone,
)
from bioma_api.services.kommo_portal import webhook_lead_ids

FIELD_TO_KEY = {name: key for key, _label, names in DIMENSIONS for name in names}

CUSTOM_FIELDS = [
    {"id": 1, "name": "Segmento", "type": "select", "enums": [{"id": 11, "value": "Dental"}, {"id": 12, "value": "Medical"}]},
    {
        "id": 2,
        "name": "Produto de Interesse",
        "type": "multiselect",
        "enums": [{"id": 21, "value": "Galileana"}, {"id": 22, "value": "Prismática"}, {"id": 23, "value": "Fotóforo"}],
    },
    {"id": 3, "name": "UF", "type": "select", "enums": [{"id": 31, "value": "SP"}, {"id": 32, "value": "MG"}]},
    {"id": 4, "name": "Solicitação inicial", "type": "select", "enums": [{"id": 41, "value": "Preço"}]},
    {"id": 5, "name": "Resumo do atendimento", "type": "textarea"},
    {"id": 6, "name": "Cidade", "type": "text"},
]
SPECS = field_specs(CUSTOM_FIELDS, FIELD_TO_KEY)


def test_so_campos_de_lista_viram_alvo():
    assert {spec.key for spec in SPECS} == {"segmento", "produto", "uf", "solicitacao"}
    produto = next(spec for spec in SPECS if spec.key == "produto")
    assert produto.multiple is True
    assert produto.options == {"Galileana": 21, "Prismática": 22, "Fotóforo": 23}


def test_uf_pelo_ddd_em_varios_formatos():
    assert uf_from_phone("+55 (11) 98765-4321") == "SP"
    assert uf_from_phone("31987654321") == "MG"
    assert uf_from_phone("3134567890") == "MG"
    assert uf_from_phone("+1 415 555 0100") is None
    assert uf_from_phone(None) is None


def test_regras_leem_so_a_fala_do_cliente():
    messages = [
        {"type": "outgoing", "text": "Temos galileana e fotóforo, quer o catálogo?", "created_at": 2},
        {"type": "incoming", "text": "Sou dentista, quanto custa a lupa prismática?", "created_at": 1},
    ]
    transcript, customer = build_state(messages)
    assert transcript.splitlines()[0].startswith("Cliente:")
    decisions = classify_with_rules(customer, "(11) 98765-4321", SPECS)
    assert decisions["segmento"]["values"] == ["Dental"]
    assert decisions["produto"]["values"] == ["Prismática"]  # galileana foi dita pelo atendente
    assert decisions["solicitacao"]["values"] == ["Preço"]
    assert decisions["uf"] == {"values": ["SP"], "confidence": 0.85, "source": "ddd"}


def test_regra_nao_inventa_opcao_que_a_conta_nao_tem():
    decisions = classify_with_rules("sou veterinario e quero um combo", None, SPECS)
    assert decisions == {}


def test_modelo_so_vale_com_confianca_e_opcao_existente():
    questions = build_questions(SPECS)
    assert "uf" not in questions
    assert UNDECIDED in questions["segmento"]["criteria"]
    answers = {
        "segmento": {"choice": "Medical", "confidence": 0.91},
        "produto": {"choice": "Galileana", "confidence": 0.41},
        "solicitacao": {"choice": UNDECIDED, "confidence": 0.95},
        "origem": {"choice": "Inventado", "confidence": 0.99},
    }
    decisions = decisions_from_answers(answers, SPECS)
    assert decisions == {"segmento": {"values": ["Medical"], "confidence": 0.91, "source": "modelo"}}


def test_modelo_prevalece_sobre_regra_menos_no_estado():
    rules = {
        "segmento": {"values": ["Dental"], "confidence": 0.7, "source": "regra"},
        "uf": {"values": ["SP"], "confidence": 0.85, "source": "ddd"},
    }
    model = {
        "segmento": {"values": ["Medical"], "confidence": 0.9, "source": "modelo"},
        "uf": {"values": ["MG"], "confidence": 0.9, "source": "modelo"},
    }
    merged = merge_decisions(model, rules)
    assert merged["segmento"]["source"] == "modelo"
    assert merged["uf"]["values"] == ["SP"]


def test_payload_nunca_sobrescreve_campo_preenchido():
    decisions = {
        "segmento": {"values": ["Dental"], "confidence": 0.7, "source": "regra"},
        "produto": {"values": ["Galileana", "Fotóforo"], "confidence": 0.7, "source": "regra"},
    }
    payload = payload_for_kommo(decisions, SPECS, already_filled={"segmento"})
    assert payload == [{"field_id": 2, "values": [{"enum_id": 21}, {"enum_id": 23}]}]


def test_webhook_extrai_leads_de_mensagem_e_de_lead_novo():
    form = {
        "account[subdomain]": "cliente",
        "message[add][0][text]": "Olá",
        "message[add][0][entity_id]": "501",
        "message[add][0][entity_type]": "lead",
        "message[add][1][entity_id]": "777",
        "message[add][1][entity_type]": "contact",
        "leads[add][0][id]": "502",
        "leads[add][0][status_id]": "142",
    }
    assert webhook_lead_ids(form) == {501, 502}


def test_test_classification_com_regras_e_ddd(monkeypatch):
    from unittest.mock import MagicMock
    from bioma_api.services import kommo_portal

    monkeypatch.setattr(kommo_portal, "connect", MagicMock())
    monkeypatch.setattr(kommo_portal, "_organization", lambda _conn, _slug: {"id": "11111111-1111-1111-1111-111111111111"})
    monkeypatch.setattr(kommo_portal, "_api", lambda _conn, _org_id: MagicMock())
    monkeypatch.setattr(kommo_portal, "_cached_field_specs", lambda _api, _org_id: SPECS)

    result = kommo_portal.test_classification("univet", "Olá, sou dentista e quero comprar lupa galileana", "11987654321")
    assert result["status"] == "classificado"
    by_key = {f["key"]: f for f in result["fields"]}
    assert "segmento" in by_key and by_key["segmento"]["values"] == ["Dental"]
    assert "produto" in by_key and by_key["produto"]["values"] == ["Galileana"]
    assert "uf" in by_key and by_key["uf"]["values"] == ["SP"]
