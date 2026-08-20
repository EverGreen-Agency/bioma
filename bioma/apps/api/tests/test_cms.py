"""Preparo de uma peça do Estúdio para publicação em CMS — decisão 14.

Você respondeu: WordPress primeiro, mas com os outros CMS no horizonte, e
rascunho-ou-direto CONFIGURÁVEL. Estes testes fixam as três consequências:

1. o padrão é rascunho, sempre;
2. configurar "direto" não vence a aprovação — peça não aprovada vira rascunho
   mesmo com a conta configurada para publicar direto;
3. o payload é montado por uma função pura, então dá para ver o que seria
   enviado sem enviar nada.
"""

import pytest

from bioma_api.cms import (
    build_post_payload,
    markdown_to_html,
    resolve_publish_status,
    slugify,
)


class TestSlug:
    def test_tira_acento_do_portugues(self):
        assert slugify("Campanha de verão na praça") == "campanha-de-verao-na-praca"

    def test_minusculas_e_hifen(self):
        assert slugify("Quanto Custa Google Ads") == "quanto-custa-google-ads"

    def test_pontuacao_vira_separador_sem_dobrar_hifen(self):
        assert slugify("SEO: o guia — completo!") == "seo-o-guia-completo"

    def test_nao_comeca_nem_termina_com_hifen(self):
        resultado = slugify("  ...marketing digital!!!  ")
        assert resultado == "marketing-digital"

    def test_titulo_so_de_simbolos_nao_vira_slug_vazio(self):
        # Slug vazio faria o WordPress inventar um, e aí o link do post não
        # bate com o que a tela mostrou.
        assert slugify("!!! ???") == ""

    def test_corta_em_limite_sem_partir_palavra(self):
        titulo = "guia completo de anuncios no google ads para advogados em 2026"
        resultado = slugify(titulo, max_length=30)
        assert len(resultado) <= 30
        assert not resultado.endswith("-")
        # Todo pedaco do slug tem que ser uma palavra INTEIRA do titulo. A
        # primeira versao deste teste afirmava outra coisa e reprovava um slug
        # correto — teste tambem erra, e por isso ele precisa ser legivel.
        palavras = set(titulo.split())
        assert all(pedaco in palavras for pedaco in resultado.split("-"))


class TestStatusDePublicacao:
    def test_padrao_e_rascunho(self):
        """Sem configuração explícita, nada vai ao ar. Publicar por engano no
        site do cliente é o erro caro; rascunho esquecido é o barato."""
        assert resolve_publish_status(artifact_status="approved", mode=None) == "draft"

    def test_modo_rascunho_manda_rascunho(self):
        assert resolve_publish_status(artifact_status="approved", mode="draft") == "draft"

    def test_modo_direto_com_peca_aprovada_publica(self):
        assert resolve_publish_status(artifact_status="approved", mode="direct") == "publish"

    @pytest.mark.parametrize("status", ["draft", "archived"])
    def test_modo_direto_nao_vence_falta_de_aprovacao(self, status):
        """A configuração diz COMO publicar, não SE a peça está pronta.
        Sem essa regra, marcar 'direto' uma vez transformaria todo rascunho
        futuro em publicação automática."""
        assert resolve_publish_status(artifact_status=status, mode="direct") == "draft"

    def test_peca_ja_publicada_no_bioma_pode_ir_direto(self):
        assert resolve_publish_status(artifact_status="published", mode="direct") == "publish"


class TestMarkdownParaHtml:
    def test_paragrafos_viram_p(self):
        assert markdown_to_html("Um.\n\nDois.") == "<p>Um.</p>\n<p>Dois.</p>"

    def test_subtitulos_viram_h2_e_h3(self):
        html = markdown_to_html("## Quanto custa?\n\n### Detalhe")
        assert "<h2>Quanto custa?</h2>" in html
        assert "<h3>Detalhe</h3>" in html

    def test_lista_vira_ul(self):
        html = markdown_to_html("- um\n- dois")
        assert html == "<ul>\n<li>um</li>\n<li>dois</li>\n</ul>"

    def test_link_e_negrito(self):
        html = markdown_to_html("Veja o [relatório](https://ex.com) e **note** isto.")
        assert '<a href="https://ex.com">relatório</a>' in html
        assert "<strong>note</strong>" in html

    def test_escapa_html_do_texto(self):
        """Texto do cliente pode conter < e >. Mandar cru abriria injeção no
        site dele — e o site é dele, não nosso, para arriscar."""
        html = markdown_to_html("comparar a < b e <script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_texto_vazio_nao_vira_p_vazio(self):
        assert markdown_to_html("") == ""


class TestPayload:
    ARTEFATO = {
        "title": "Quanto custa anunciar no Google Ads",
        "content": "O mínimo é R$ 1.500.\n\n## Como calcular?\n\n- ticket médio\n- CPC alvo",
        "status": "approved",
    }

    def test_monta_o_payload_do_wordpress(self):
        payload = build_post_payload(self.ARTEFATO, mode="draft")
        assert payload["title"] == "Quanto custa anunciar no Google Ads"
        assert payload["status"] == "draft"
        assert payload["slug"] == "quanto-custa-anunciar-no-google-ads"
        assert "<h2>Como calcular?</h2>" in payload["content"]

    def test_resumo_sai_do_primeiro_paragrafo(self):
        payload = build_post_payload(self.ARTEFATO, mode="draft")
        assert payload["excerpt"] == "O mínimo é R$ 1.500."

    def test_resumo_longo_corta_em_palavra_inteira(self):
        artefato = {**self.ARTEFATO, "content": "palavra " * 60}
        payload = build_post_payload(artefato, mode="draft")
        assert len(payload["excerpt"]) <= 160
        assert not payload["excerpt"].rstrip(".").endswith("palav")

    def test_slug_explicito_vence_o_derivado_do_titulo(self):
        payload = build_post_payload(self.ARTEFATO, mode="draft", slug="promo-google-ads")
        assert payload["slug"] == "promo-google-ads"

    def test_peca_sem_conteudo_e_recusada(self):
        """Publicar post vazio no site do cliente é pior do que não publicar."""
        with pytest.raises(ValueError, match="conteúdo"):
            build_post_payload({**self.ARTEFATO, "content": ""}, mode="draft")

    def test_categorias_e_tags_so_entram_quando_informadas(self):
        """Mandar lista vazia limparia as categorias no WordPress; omitir deixa
        o CMS aplicar o padrão dele."""
        payload = build_post_payload(self.ARTEFATO, mode="draft")
        assert "categories" not in payload
        assert "tags" not in payload

        com_taxonomia = build_post_payload(self.ARTEFATO, mode="draft", categories=[3], tags=[7, 9])
        assert com_taxonomia["categories"] == [3]
        assert com_taxonomia["tags"] == [7, 9]

    def test_o_payload_nao_inventa_autor_nem_data(self):
        """Campo que a EG não sabe fica fora: `author` errado publica em nome
        de outra pessoa, e `date` errado joga o post para o passado."""
        payload = build_post_payload(self.ARTEFATO, mode="draft")
        assert "author" not in payload
        assert "date" not in payload
