"""Derivação de métricas de Performance — casos de borda de divisão por zero.

A auditoria de 2026-07-12 citou `_derive_ads_metrics` com métricas zeradas
como exemplo do que smoke não cobre. Campanha pausada (0 impressões, 0 cliques,
0 custo) é o caso real mais comum e é justamente onde uma divisão desprotegida
viraria `ZeroDivisionError` na resposta da API.
"""

from decimal import Decimal

from bioma_api.services.performance import _as_float, _as_int, _derive_ads_metrics


class TestNumericCoercion:
    def test_none_vira_zero(self):
        assert _as_int(None) == 0
        assert _as_float(None) == 0.0

    def test_decimal_do_postgres_converte(self):
        assert _as_int(Decimal("42")) == 42
        assert _as_float(Decimal("3.5")) == 3.5

    def test_string_vazia_nao_explode(self):
        assert _as_int("") == 0
        assert _as_float("") == 0.0


class TestDeriveAdsMetrics:
    def test_campanha_zerada_nao_divide_por_zero(self):
        # 0 impressões / 0 cliques / 0 custo: todas as razões caem para 0.
        result = _derive_ads_metrics(
            {"impressions": 0, "clicks": 0, "cost_micros": 0, "conversions": 0}
        )
        assert result["ctr"] == 0
        assert result["cpc_micros"] == 0
        assert result["cpa_micros"] == 0
        assert result["roas"] == 0

    def test_linha_none_nao_explode(self):
        result = _derive_ads_metrics(None)
        assert result["ctr"] == 0
        assert result["roas"] == 0

    def test_ctr_calculado(self):
        result = _derive_ads_metrics({"impressions": 1000, "clicks": 50})
        assert result["ctr"] == 0.05

    def test_cost_micros_para_reais_no_roas(self):
        # cost_micros = 2_000_000 → custo 2.0; valor de conversão 6.0 → ROAS 3.0.
        result = _derive_ads_metrics(
            {"impressions": 10, "clicks": 5, "cost_micros": 2_000_000, "conversion_value": 6}
        )
        assert result["roas"] == 3.0

    def test_cliques_sem_impressao_nao_quebra_ctr(self):
        # Estado inconsistente da fonte: cliques > 0 com impressões 0.
        result = _derive_ads_metrics({"impressions": 0, "clicks": 5})
        assert result["ctr"] == 0

    def test_conversoes_zero_protege_cpa(self):
        result = _derive_ads_metrics(
            {"impressions": 100, "clicks": 10, "cost_micros": 500_000, "conversions": 0}
        )
        assert result["cpa_micros"] == 0
