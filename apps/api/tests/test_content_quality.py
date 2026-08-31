"""Score de prontidão SEO/GEO de um texto — decisão 14.

O que este módulo é: uma CHECKLIST executável sobre o texto que está na mão.
O que ele NÃO é: previsão de posição no Google. Nenhum sinal aqui vem de fora
(autoridade de domínio, backlinks, concorrência), e prometer ranking a partir
do texto seria exatamente o tipo de número inventado que não entra no produto.

GEO (Generative Engine Optimization) é o eixo novo: o que faz um trecho ser
CITADO por um motor generativo é diferente do que o faz ranquear. Resposta logo
no começo, subtítulo em forma de pergunta, dado com fonte ao lado.
"""

import pytest

from bioma_api.content_quality import evaluate_content


ARTIGO_BOM = """
Quanto custa anunciar no Google Ads em 2026?

O investimento mínimo recomendado para uma campanha de busca no Brasil é de
R$ 1.500 por mês, segundo o [relatório de benchmarks da EverGreen](https://evergreenmkt.com.br/benchmarks).
Abaixo disso o algoritmo não reúne dados suficientes para otimizar.

## Como o orçamento é calculado?

O Google cobra por clique, e o custo por clique varia por setor. Em serviços
jurídicos o CPC médio ficou em R$ 8,40 em 2026, contra R$ 2,10 em e-commerce
de moda, de acordo com [dados públicos do Google](https://ads.google.com).

- Defina o CPC alvo a partir do seu ticket médio
- Reserve 30% do orçamento para testes
- Só escale campanha com dado de conversão confiável

## Vale a pena para negócio local?

Sim. Campanhas locais costumam ter CPC menor porque a concorrência é limitada
ao raio de atendimento. A EverGreen acompanha esse recorte no Radar Local.

![Gráfico de CPC médio por setor em 2026](https://exemplo.com/cpc.png)

Atualizado em março de 2026.
"""


def test_texto_vazio_nao_quebra_e_nao_pontua():
    relatorio = evaluate_content("", title="")
    assert relatorio["score"] == 0
    assert relatorio["checks"], "precisa dizer o que faltou, não devolver lista vazia"


def test_score_fica_sempre_entre_0_e_100():
    for texto in ["", "oi", ARTIGO_BOM, ARTIGO_BOM * 10]:
        relatorio = evaluate_content(texto, title="Quanto custa anunciar no Google Ads em 2026?")
        assert 0 <= relatorio["score"] <= 100
        assert 0 <= relatorio["seo_score"] <= 100
        assert 0 <= relatorio["geo_score"] <= 100


def test_artigo_bem_estruturado_pontua_alto():
    relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa anunciar no Google Ads em 2026?")
    assert relatorio["score"] >= 70, [c["id"] for c in relatorio["checks"] if not c["passed"]]


def test_texto_solto_nao_engana_o_score():
    """Parágrafo único, sem estrutura, sem fonte. Tem que pontuar baixo —
    um score generoso aqui destruiria a utilidade da checklist inteira."""
    relatorio = evaluate_content("Fale com a gente hoje mesmo e turbine seus resultados!", title="Marketing")
    assert relatorio["score"] < 40


class TestChecksDeSeo:
    def test_titulo_curto_demais_reprova(self):
        relatorio = evaluate_content(ARTIGO_BOM, title="Ads")
        assert _check(relatorio, "titulo_tamanho")["passed"] is False

    def test_titulo_no_tamanho_aprova(self):
        relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa anunciar no Google Ads em 2026")
        assert _check(relatorio, "titulo_tamanho")["passed"] is True

    def test_imagem_sem_alt_reprova(self):
        texto = ARTIGO_BOM.replace("![Gráfico de CPC médio por setor em 2026]", "![]")
        relatorio = evaluate_content(texto, title="Quanto custa anunciar no Google Ads em 2026")
        assert _check(relatorio, "imagem_alt")["passed"] is False

    def test_sem_subtitulo_reprova_estrutura(self):
        relatorio = evaluate_content("Um texto corrido bem longo. " * 60, title="Título de tamanho adequado aqui")
        assert _check(relatorio, "subtitulos")["passed"] is False

    def test_palavra_chave_no_titulo_e_no_inicio(self):
        relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa Google Ads", keyword="Google Ads")
        assert _check(relatorio, "keyword_titulo")["passed"] is True
        assert _check(relatorio, "keyword_inicio")["passed"] is True

    def test_sem_palavra_chave_informada_o_check_nao_aparece(self):
        """Reprovar por uma keyword que ninguém informou seria punir o texto por
        uma escolha que não foi feita."""
        relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa Google Ads")
        assert _opcional(relatorio, "keyword_titulo") is None


class TestChecksDeGeo:
    def test_resposta_logo_no_inicio_aprova(self):
        relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa anunciar no Google Ads")
        assert _check(relatorio, "resposta_no_inicio")["passed"] is True

    def test_texto_que_enrola_antes_de_responder_reprova(self):
        enrolado = (
            "Muita gente se pergunta sobre isso. Antes de responder, vale entender "
            "o contexto histórico do mercado publicitário brasileiro e sua evolução "
            "ao longo das últimas décadas, um tema que rende boas conversas. "
        ) * 3 + "\n\nO custo mínimo é R$ 1.500 por mês."
        relatorio = evaluate_content(enrolado, title="Quanto custa anunciar no Google Ads")
        assert _check(relatorio, "resposta_no_inicio")["passed"] is False

    def test_subtitulo_em_pergunta_aprova(self):
        relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa anunciar no Google Ads")
        assert _check(relatorio, "subtitulo_pergunta")["passed"] is True

    def test_numero_sem_fonte_ao_lado_reprova(self):
        """Motor generativo cita o que consegue atribuir. Número solto é o tipo
        de coisa que ele prefere não repetir."""
        texto = "## Quanto custa?\n\nO custo é R$ 1.500 por mês e o CPC é R$ 8,40.\n\n- um\n- dois\n"
        relatorio = evaluate_content(texto, title="Quanto custa anunciar no Google Ads")
        assert _check(relatorio, "dado_com_fonte")["passed"] is False

    def test_numero_com_link_na_mesma_frase_aprova(self):
        relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa anunciar no Google Ads")
        assert _check(relatorio, "dado_com_fonte")["passed"] is True

    def test_lista_escaneavel_aprova(self):
        relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa anunciar no Google Ads")
        assert _check(relatorio, "lista")["passed"] is True


def test_check_que_nao_se_aplica_nao_vira_ponto_de_graca():
    """Texto sem imagem nenhuma nao "passa" no check de alt: ele nao se aplica.

    Contar como aprovado dava 6 pontos a um texto VAZIO — foi o teste de texto
    vazio que revelou isso, e a correcao virou o campo `applicable`."""
    relatorio = evaluate_content("", title="")
    alt = _check(relatorio, "imagem_alt")
    assert alt["applicable"] is False
    assert alt["passed"] is False


def test_toda_falha_explica_o_que_fazer():
    """Score sem instrução é só um número que julga."""
    relatorio = evaluate_content("nada", title="x")
    for check in relatorio["checks"]:
        if not check["passed"]:
            assert check["hint"], f"{check['id']} reprova sem dizer como corrigir"


def test_familias_sao_pontuadas_separadamente():
    """SEO e GEO puxam para lados diferentes; uma média única esconderia isso."""
    relatorio = evaluate_content(ARTIGO_BOM, title="Quanto custa anunciar no Google Ads em 2026")
    familias = {check["family"] for check in relatorio["checks"]}
    assert familias == {"seo", "geo"}


def _check(relatorio, check_id):
    encontrado = _opcional(relatorio, check_id)
    assert encontrado is not None, f"check '{check_id}' não existe no relatório"
    return encontrado


def _opcional(relatorio, check_id):
    return next((c for c in relatorio["checks"] if c["id"] == check_id), None)
