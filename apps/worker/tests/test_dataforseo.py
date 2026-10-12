from datetime import datetime

import pytest

from bioma_worker.dataforseo import DataForSeoError, normalize_domain_rank_response


def test_normaliza_snapshot_com_dados_sem_inventar_campos():
    payload = {
        "status_code": 20000,
        "status_message": "Ok.",
        "cost": 0.0101,
        "tasks": [{
            "id": "task-real-contract",
            "status_code": 20000,
            "cost": 0.0101,
            "result": [{
                "location_code": 2076,
                "language_code": "pt",
                "items": [{
                    "location_code": 2076,
                    "language_code": "pt",
                    "metrics": {
                        "organic": {"count": 19, "etv": 31.5, "pos_1": 2},
                        "paid": {"count": 0, "etv": 0},
                    },
                }],
            }],
        }],
    }

    result = normalize_domain_rank_response(payload, "evergreenmkt.com.br")

    assert result["has_data"] is True
    assert result["organic"] == {"count": 19, "etv": 31.5, "pos_1": 2}
    assert result["paid"] == {"count": 0, "etv": 0}
    assert result["source_task_id"] == "task-real-contract"
    assert result["raw_response"] is payload
    assert isinstance(result["measured_at"], datetime)


def test_normaliza_resposta_valida_sem_dados():
    payload = {
        "status_code": 20000,
        "tasks": [{"id": "empty", "status_code": 20000, "result": [{"items": []}]}],
    }

    result = normalize_domain_rank_response(payload, "evergreenmkt.com.br")

    assert result["has_data"] is False
    assert result["organic"] == {}


def test_recusa_erro_de_tarefa():
    payload = {
        "status_code": 20000,
        "tasks": [{"status_code": 40501, "status_message": "Invalid Field", "result": []}],
    }

    with pytest.raises(DataForSeoError, match="40501"):
        normalize_domain_rank_response(payload, "evergreenmkt.com.br")
