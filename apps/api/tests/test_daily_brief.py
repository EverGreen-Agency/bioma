"""Resumo diário do cockpit — decisão 3.

Você escolheu a opção A: um card no cockpit ao abrir, sem push por evento. A
regra que atravessa tudo aqui é **não encher**: um resumo que fala todo dia,
mesmo quando não há nada, treina a pessoa a fechar sem ler — e aí ele deixa de
funcionar justamente no dia em que tem algo.
"""

from bioma_api.daily_brief import compose_brief


VAZIO = {
    "overdue_items": [],
    "pending_approvals": [],
    "stale_connections": [],
    "radar_prospects_awaiting": 0,
    "clients_at_risk": 0,
}


def test_dia_limpo_nao_inventa_assunto():
    """Sem nada pendente, o resumo diz isso — e não enche com métrica de
    enfeite só para ter o que mostrar."""
    brief = compose_brief(VAZIO)
    assert brief["items"] == []
    assert brief["clear"] is True


def test_atraso_vem_antes_de_aprovacao_que_vem_antes_de_conexao():
    """A ordem é por CUSTO DE NÃO AGIR, não por quantidade.

    Entrega atrasada já quebrou um combinado com o cliente; aprovação parada
    está prestes a quebrar; conexão velha degrada dado que ninguém olha hoje.
    Ordenar por contagem colocaria 40 conexões antes de 1 entrega atrasada."""
    brief = compose_brief({
        **VAZIO,
        "overdue_items": [{"title": "Post de lançamento"}],
        "pending_approvals": [{"title": "Proposta Univet"}, {"title": "Proposta HM"}],
        "stale_connections": [{"provider": "meta_ads"}, {"provider": "ga4"}, {"provider": "gtm"}],
    })
    assert [item["kind"] for item in brief["items"]] == ["overdue", "approval", "stale_connection"]
    assert brief["clear"] is False


def test_conta_certo_e_singulariza():
    brief = compose_brief({**VAZIO, "overdue_items": [{"title": "Só um"}]})
    item = brief["items"][0]
    assert item["count"] == 1
    assert "1 entrega atrasada" in item["title"]

    brief = compose_brief({**VAZIO, "overdue_items": [{"title": "A"}, {"title": "B"}]})
    assert "2 entregas atrasadas" in brief["items"][0]["title"]


def test_cita_exemplos_mas_nao_despeja_a_lista_inteira():
    """O card é um resumo. Listar 40 itens transformaria ele na própria tela
    que ele deveria resumir."""
    brief = compose_brief({
        **VAZIO,
        "overdue_items": [{"title": f"Entrega {n}"} for n in range(40)],
    })
    item = brief["items"][0]
    assert item["count"] == 40
    assert len(item["examples"]) <= 3
    assert item["examples"][0] == "Entrega 0"


def test_prospect_do_radar_entra_como_oportunidade_nao_como_alarme():
    """Prospect esperando não é falha — é fila. Marcar como crítico junto com
    entrega atrasada apagaria a diferença entre as duas coisas."""
    brief = compose_brief({**VAZIO, "radar_prospects_awaiting": 7})
    item = next(i for i in brief["items"] if i["kind"] == "radar")
    assert item["severity"] == "info"
    assert item["count"] == 7


def test_cliente_em_risco_e_o_mais_grave():
    brief = compose_brief({
        **VAZIO,
        "clients_at_risk": 2,
        "overdue_items": [{"title": "X"}],
    })
    assert brief["items"][0]["kind"] == "client_risk"
    assert brief["items"][0]["severity"] == "critical"


def test_toda_linha_diz_para_onde_ir():
    """Resumo sem destino vira notícia. A pessoa precisa poder clicar."""
    brief = compose_brief({
        "overdue_items": [{"title": "A"}],
        "pending_approvals": [{"title": "B"}],
        "stale_connections": [{"provider": "ga4"}],
        "radar_prospects_awaiting": 3,
        "clients_at_risk": 1,
    })
    assert len(brief["items"]) == 5
    for item in brief["items"]:
        assert item["href"], f"{item['kind']} não diz para onde ir"


def test_campos_ausentes_nao_quebram():
    """O cockpit pode ganhar ou perder campo; o resumo não pode cair por isso."""
    brief = compose_brief({})
    assert brief["clear"] is True
