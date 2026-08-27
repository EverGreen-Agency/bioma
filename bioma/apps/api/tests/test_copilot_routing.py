from bioma_api.services.copilot import _eligible_routing_candidates


def test_copilot_remove_candidatos_inelegiveis_antes_de_executar():
    ranked = [
        {"model_id": "sem-cota", "eligible": False, "allow_fallback": True},
        {"model_id": "pronto", "eligible": True, "allow_fallback": True},
    ]
    assert [candidate["model_id"] for candidate in _eligible_routing_candidates(ranked)] == ["pronto"]


def test_politica_sem_fallback_tenta_so_o_primeiro_elegivel():
    ranked = [
        {"model_id": "escolhido", "eligible": True, "allow_fallback": False},
        {"model_id": "nao-deve-rodar", "eligible": True, "allow_fallback": True},
    ]
    assert [candidate["model_id"] for candidate in _eligible_routing_candidates(ranked)] == ["escolhido"]
