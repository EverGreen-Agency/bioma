"""Painel de dados reais do Kommo (`bioma_api.kommo_insights`).

Fixam as duas regras que dão sentido ao painel: nenhum dado pessoal sobrevive à
compactação, e os números do recorte batem com os leads que caem na janela.
"""

from bioma_api.kommo_insights import (
    LOST_STATUS_ID,
    WON_STATUS_ID,
    build_dashboard,
    compact_lead,
    compact_pipelines,
)

DAY = 86400
NOW = 1_800_000_000.0

PIPELINES = compact_pipelines(
    [
        {
            "id": 1,
            "name": "Inbound",
            "is_main": True,
            "_embedded": {
                "statuses": [
                    {"id": 143, "name": "Venda perdida", "sort": 30},
                    {"id": 10, "name": "Primeiro atendimento", "sort": 10},
                    {"id": 142, "name": "Venda ganha", "sort": 20},
                ]
            },
        }
    ]
)


def raw_lead(lead_id, days_ago, status_id=10, price=0, fields=None, loss=None):
    lead = {
        "id": lead_id,
        "name": "Dr. Fulano de Tal",
        "created_at": int(NOW - days_ago * DAY),
        "updated_at": int(NOW - days_ago * DAY + 60),
        "closed_at": None,
        "pipeline_id": 1,
        "status_id": status_id,
        "price": price,
        "custom_fields_values": [
            {"field_name": name, "values": [{"value": v} for v in values]} for name, values in (fields or {}).items()
        ],
        "_embedded": {"loss_reason": [{"name": loss}] if loss else []},
    }
    return compact_lead(lead)


def test_compact_lead_descarta_dado_pessoal_e_normaliza_campos():
    lead = raw_lead(
        1,
        3,
        fields={
            "Origem do lead": ["Google Ads"],
            "Produto de Interesse": ["Galileana", "Fotóforo"],
            "UF": ["SP"],
            "utm_source": ["google"],
            "Data da visita/agendamento": [1799999999],
            "Resumo do atendimento": ["Ligou pedindo preço, CPF 000.000.000-00"],
            "Cidade": ["Campinas"],
        },
    )
    assert "name" not in lead
    assert lead["dims"] == {"origem": ["Google Ads"], "produto": ["Galileana", "Fotóforo"], "uf": ["SP"]}
    assert lead["utm"] == {"source": "google"}
    assert lead["has_visit"] is True
    assert "CPF" not in str(lead)


def test_recorte_por_periodo_e_periodo_anterior():
    leads = [raw_lead(i, days) for i, days in enumerate([1, 10, 29, 40, 55, 200])]
    dashboard = build_dashboard(leads, PIPELINES, 30, NOW)
    assert dashboard["totals"]["leads"] == 3
    assert dashboard["totals"]["leads_previous"] == 2
    assert dashboard["totals"]["leads_all_time"] == 6
    assert sum(bucket["leads"] for bucket in dashboard["timeline"]) == 3

    tudo = build_dashboard(leads, PIPELINES, 0, NOW)
    assert tudo["totals"]["leads"] == 6
    assert tudo["totals"]["leads_previous"] is None
    assert sum(bucket["leads"] for bucket in tudo["timeline"]) == 6


def test_funil_ordena_etapas_e_separa_ganho_e_perdido():
    leads = [
        raw_lead(1, 2),
        raw_lead(2, 2, status_id=WON_STATUS_ID, price=18000),
        raw_lead(3, 2, status_id=LOST_STATUS_ID, loss="Preço"),
        raw_lead(4, 2, price=9000),
    ]
    dashboard = build_dashboard(leads, PIPELINES, 30, NOW)
    stages = dashboard["pipelines"][0]["stages"]
    assert [stage["name"] for stage in stages] == ["Primeiro atendimento", "Venda ganha", "Venda perdida"]
    assert [stage["kind"] for stage in stages] == ["open", "won", "lost"]
    assert [stage["count"] for stage in stages] == [2, 1, 1]
    totals = dashboard["totals"]
    assert (totals["open"], totals["won"], totals["lost"]) == (2, 1, 1)
    assert totals["won_value"] == 18000
    assert totals["open_value"] == 9000
    assert dashboard["loss_reasons"] == [{"label": "Preço", "count": 1, "share": 1.0}]


def test_qualidade_mede_preenchimento_sobre_o_recorte():
    leads = [
        raw_lead(1, 1, fields={"Segmento": ["Dental"], "UF": ["SP"]}),
        raw_lead(2, 1, fields={"Segmento": ["Medical"]}),
        raw_lead(3, 1),
        raw_lead(4, 1, price=500),
    ]
    dashboard = build_dashboard(leads, PIPELINES, 30, NOW)
    quality = {row["key"]: row for row in dashboard["quality"]}
    assert (quality["segmento"]["filled"], quality["segmento"]["total"]) == (2, 4)
    assert quality["uf"]["filled"] == 1
    assert quality["valor"]["filled"] == 1
    assert quality["utm"]["filled"] == 0
    segmento = next(d for d in dashboard["dimensions"] if d["key"] == "segmento")
    assert {item["label"]: item["share"] for item in segmento["items"]} == {"Dental": 0.5, "Medical": 0.5}


def test_sem_leads_devolve_painel_vazio_sem_quebrar():
    dashboard = build_dashboard([], PIPELINES, 90, NOW)
    assert dashboard["totals"]["leads"] == 0
    assert dashboard["timeline"] == []
    assert dashboard["totals"]["last_lead_at"] is None
    assert dashboard["pipelines"][0]["leads"] == 0
