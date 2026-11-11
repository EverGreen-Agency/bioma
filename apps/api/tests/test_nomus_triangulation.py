"""Testes unitários para o motor de conciliação / triangulação determinística Nomus ERP <-> Kommo CRM."""

from typing import Any
from unittest.mock import patch

from bioma_api.services.nomus_service import (
    clean_document_digits,
    compute_nomus_analytics,
    index_kommo_leads,
    normalize_client_name,
    normalize_email_address,
    normalize_phone_match_keys,
    reconcile_order_with_kommo,
    resolve_marketing_channel_from_lead,
)


def test_clean_document_digits():
    assert clean_document_digits("065.439.429-67") == "06543942967"
    assert clean_document_digits("66.581.935/0001-17") == "66581935000117"
    assert clean_document_digits("12345") is None
    assert clean_document_digits(None) is None


def test_normalize_phone_match_keys():
    keys = normalize_phone_match_keys("+55 (43) 8406-0200")
    assert "4384060200" in keys
    assert "br_43_84060200" in keys
    assert "5543984060200" in keys

    # Celular com nono dígito pareia com chave sem o nono dígito
    keys_9d = normalize_phone_match_keys("+55 11 98234-1122")
    assert "br_11_82341122" in keys_9d


def test_normalize_email_address():
    assert normalize_email_address("  Paulo.Rossato@Outlook.com ") == "paulo.rossato@outlook.com"
    assert normalize_email_address("invalid-email") is None
    assert normalize_email_address(None) is None


def test_resolve_marketing_channel():
    lead_google = {
        "utm": {"source": "google", "campaign": "Search Loupes"},
        "dims": {"origem": ["Google Ads"]},
    }
    assert resolve_marketing_channel_from_lead(lead_google) == "Google Ads (Search Loupes)"

    lead_meta = {
        "utm": {"source": "facebook", "campaign": "Instagram Stories"},
        "dims": {"origem": ["Meta Ads"]},
    }
    assert resolve_marketing_channel_from_lead(lead_meta) == "Meta Ads (Instagram Stories)"

    lead_whats = {
        "utm": {},
        "dims": {"origem": ["WhatsApp Indicação"]},
    }
    assert resolve_marketing_channel_from_lead(lead_whats) == "WhatsApp (Indicação Direta)"


def test_reconciliation_waterfall_tiers():
    leads = [
        {
            "id": 101,
            "documents": ["06543942967"],
            "phones": ["4384060200"],
            "emails": ["paulo@exemplo.com"],
            "utm": {"source": "google", "campaign": "Search"},
            "dims": {"uf": ["PR"]},
            "created_at": 1700000000,
        },
        {
            "id": 102,
            "documents": [],
            "phones": ["11999887766"],
            "emails": ["vanessa@exemplo.com"],
            "utm": {"source": "meta", "campaign": "Reels"},
            "dims": {"uf": ["SP"]},
            "created_at": 1700000000,
        },
        {
            "id": 103,
            "documents": [],
            "phones": [],
            "emails": ["contato@faria.com"],
            "utm": {},
            "dims": {"uf": ["RJ"]},
            "created_at": 1700000000,
        },
        {
            "id": 104,
            "documents": [],
            "phones": [],
            "emails": [],
            "name": "Dr. Fernando Silveira",
            "utm": {},
            "dims": {"uf": ["MG"]},
            "status_id": 142,
            "created_at": 1700000000,
        },
    ]
    indices = index_kommo_leads(leads)

    # Tier 1: Match por Documento
    cli_doc = {"cpf": "065.439.429-67", "nome": "Paulo Rossato", "uf": "PR"}
    st, lid, origem, method = reconcile_order_with_kommo(cli_doc, indices, 1700100000)
    assert st == "conciliado"
    assert lid == 101
    assert method == "cpf_cnpj"
    assert "Google Ads" in origem

    # Tier 2: Match por Telefone
    cli_tel = {"telefone": "+55 11 99988-7766", "nome": "Outro Nome", "uf": "SP"}
    st, lid, origem, method = reconcile_order_with_kommo(cli_tel, indices, 1700100000)
    assert st == "conciliado"
    assert lid == 102
    assert method == "telefone"
    assert "Meta Ads" in origem

    # Tier 3: Match por E-mail
    cli_em = {"email": " Contato@Faria.com ", "nome": "Cliente Sem Tel", "uf": "RJ"}
    st, lid, origem, method = reconcile_order_with_kommo(cli_em, indices, 1700100000)
    assert st == "conciliado"
    assert lid == 103
    assert method == "email"

    # Tier 4: Match por Nome e UF
    cli_nome = {"nome": "Fernando Silveira", "uf": "MG"}
    st, lid, origem, method = reconcile_order_with_kommo(cli_nome, indices, 1700100000)
    assert st == "conciliado"
    assert lid == 104
    assert method == "nome_territorio"

    # Fallback: Sem correspondência -> Venda Direta ERP
    cli_avulso = {"nome": "Desconhecido Sem Match", "uf": "AM"}
    st, lid, origem, method = reconcile_order_with_kommo(cli_avulso, indices, 1700100000)
    assert st == "direto_erp"
    assert lid is None
    assert method == "direto_erp"
    assert origem == "Venda Direta / Representante"


def test_compute_nomus_analytics_integration():
    mock_data = {
        "pedidos": [
            {
                "id": 1,
                "codigoPedido": "PD 0001",
                "valorTotal": "16.800,00",
                "idPessoaCliente": 10,
                "idPessoaVendedor": 161,
                "dataEmissao": "10/11/2026 10:00:00",
                "itensPedido": [{"observacoes": "Lupa Ergo HD", "quantidade": 1, "valorUnitario": "16.800,00"}],
            },
            {
                "id": 2,
                "codigoPedido": "PD 0002",
                "valorTotal": "5.000,00",
                "idPessoaCliente": 20,
                "idPessoaVendedor": 161,
                "dataEmissao": "10/11/2026 11:00:00",
                "itensPedido": [{"observacoes": "Acessórios", "quantidade": 1, "valorUnitario": "5.000,00"}],
            },
            # Pedido de vendedor Safety (ID 140) deve ser expurgado
            {
                "id": 3,
                "codigoPedido": "PD 0003",
                "valorTotal": "50,00",
                "idPessoaCliente": 30,
                "idPessoaVendedor": 140,
                "dataEmissao": "10/11/2026 12:00:00",
                "itensPedido": [],
            },
        ],
        "representantes": [{"id": 161, "nome": "Bruno Loupes"}, {"id": 140, "nome": "Victor Safety"}],
        "vendedores": [],
        "clients_cache": {
            10: {"id": 10, "nome": "Paulo Rossato", "cpf": "065.439.429-67", "uf": "PR", "telefone": "+55 43 84060200"},
            20: {"id": 20, "nome": "Cliente Balcão", "uf": "SP"},
        },
    }

    leads = [
        {
            "id": 9999,
            "documents": ["06543942967"],
            "utm": {"source": "google", "campaign": "Search Loupes"},
            "created_at": 1700000000,
        }
    ]

    with patch("bioma_api.services.nomus_service.get_cached_nomus_data", return_value=mock_data):
        res = compute_nomus_analytics(days=0, leads=leads, exclude_safety=True)

        assert res["pedidos_count"] == 2  # O pedido do Victor Safety foi expurgado
        assert res["faturamento_total"] == 21800.0
        assert res["triangulation"]["conciliated_orders_count"] == 1
        assert res["triangulation"]["conciliated_revenue"] == 16800.0
        assert res["triangulation"]["direct_orders_count"] == 1
        assert res["triangulation"]["direct_revenue"] == 5000.0

        audited = res["audited_orders"]
        assert len(audited) == 2
        order_conciliated = next(o for o in audited if o["codigo_pedido"] == "PD 0001")
        assert order_conciliated["status_triangulacao"] == "conciliado"
        assert order_conciliated["lead_id"] == 9999
        assert order_conciliated["match_method"] == "cpf_cnpj"
        assert "Google Ads" in order_conciliated["origem_canal"]

        order_direct = next(o for o in audited if o["codigo_pedido"] == "PD 0002")
        assert order_direct["status_triangulacao"] == "direto_erp"
        assert order_direct["lead_id"] is None
        assert order_direct["match_method"] == "direto_erp"

