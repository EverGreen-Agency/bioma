import pytest
from bioma_worker.integrations.kommo_deduplication import (
    KommoDeduplicationEngine,
    normalize_brazilian_phone,
    normalize_email,
)


def test_normalize_brazilian_phone_variations():
    # 1. Celular com DDD e 9 dígitos com máscara
    canon1, key1 = normalize_brazilian_phone("(11) 98765-4321")
    assert canon1 == "+5511987654321"

    # 2. Celular sem o 9 inicial (formato antigo/legado)
    canon2, key2 = normalize_brazilian_phone("1187654321")
    assert canon2 == "+5511987654321"

    # 3. Chave de match deve ser IDÊNTICA entre celular com e sem o 9
    assert key1 == key2

    # 4. Celular com DDI +55
    canon3, key3 = normalize_brazilian_phone("+55 11 98765-4321")
    assert canon3 == "+5511987654321"
    assert key3 == key1

    # 5. Telefone fixo (não deve acrescentar 9)
    canon_fixo, key_fixo = normalize_brazilian_phone("(11) 3456-7890")
    assert canon_fixo == "+551134567890"
    assert key_fixo != key1

    # 6. Inválido
    canon_inv, key_inv = normalize_brazilian_phone("invalido")
    assert canon_inv is None
    assert key_inv is None


def test_normalize_email():
    assert normalize_email("  Dr.Silva@Gmail.COM  ") == "dr.silva@gmail.com"
    assert normalize_email("invalido") is None
    assert normalize_email("") is None


def test_cluster_detection_and_lead_preservation():
    engine = KommoDeduplicationEngine(subdomain="test", access_token="mock")

    # Cenário simulado do incidente:
    # Contato 101 veio do WhatsApp na primeira importação
    # Contato 102 veio na segunda importação (com máscara diferente ou sem o 9)
    # Contato 200 é outro médico sem duplicata
    contacts = [
        {
            "id": 101,
            "name": "Dr. Roberto Silva Cirurgião",
            "created_at": 1700000000,
            "custom_fields_values": [
                {
                    "field_code": "PHONE",
                    "values": [{"value": "+55 11 98765-4321"}],
                },
                {
                    "field_code": "EMAIL",
                    "values": [{"value": "dr.roberto@clinica.com"}],
                },
            ],
            "_embedded": {
                "leads": [{"id": 1001}]
            },
        },
        {
            "id": 102,
            "name": "Roberto Silva",
            "created_at": 1705000000,
            "custom_fields_values": [
                {
                    "field_code": "PHONE",
                    "values": [{"value": "1187654321"}],  # Sem o 9
                }
            ],
            "_embedded": {
                # Segundo lead (ex: nova cotação de lupa)
                "leads": [{"id": 1002}]
            },
        },
        {
            "id": 200,
            "name": "Dra. Beatriz Santos",
            "created_at": 1706000000,
            "custom_fields_values": [
                {
                    "field_code": "PHONE",
                    "values": [{"value": "+55 21 99999-1111"}],
                }
            ],
            "_embedded": {
                "leads": [{"id": 2001}]
            },
        },
    ]

    clusters = engine.build_clusters(contacts)

    # Apenas 1 cluster deve ser formado (entre 101 e 102)
    assert len(clusters) == 1
    cluster = clusters[0]

    # O Master deve ser o 101 (mais completo e com mais dados)
    assert cluster.master_contact_id == 101
    assert cluster.master_name == "Dr. Roberto Silva Cirurgião"

    # O contato duplicado identificado é o 102
    assert len(cluster.duplicate_contacts) == 1
    assert cluster.duplicate_contacts[0]["id"] == 102

    # CRÍTICO: O lead 1002 deve ser marcado para reatribuição ao Master 101!
    assert 1002 in cluster.leads_to_reassign
    assert len(cluster.leads_to_reassign) == 1
