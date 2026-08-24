"""Transporte HTTP para o WordPress — decisão 14.

Alvo real: a EG já roda WordPress headless em `cms.evergreenmkt.com.br`, com
Application Passwords habilitado (confirmado no `/wp-json/` do site em
2026-08-11). O site Next.js da EG consome esse mesmo CMS.

Os testes usam `httpx.MockTransport`: a requisição é montada de verdade e
inspecionada de verdade, sem sair para a rede. O que se prova aqui é o que a
EG controla — URL, cabeçalho, leitura da resposta e tradução do erro. O que
depende do WordPress do outro lado continua precisando de um teste manual
contra o site.
"""

import base64
import json

import httpx
import pytest

from bioma_api.integrations.wordpress import WordPressClient, WordPressError


def _cliente(handler, site="https://cms.evergreenmkt.com.br", senha="abcd EFGH ijkl"):
    return WordPressClient(
        site_url=site,
        username="eduardo",
        app_password=senha,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


class TestEndereco:
    @pytest.mark.parametrize(
        "informado",
        [
            "https://cms.evergreenmkt.com.br",
            "https://cms.evergreenmkt.com.br/",
            "https://cms.evergreenmkt.com.br/wp-json",
            "https://cms.evergreenmkt.com.br/wp-json/wp/v2",
            "https://cms.evergreenmkt.com.br/wp-json/wp/v2/",
        ],
    )
    def test_aceita_a_url_em_qualquer_das_formas_que_a_pessoa_tem_em_maos(self, informado):
        """A pessoa copia o que tem: a home do site, ou o endpoint que já usa em
        outro lugar. Exigir uma forma específica é transformar um detalhe em
        chamado de suporte."""
        visto = {}

        def handler(request):
            visto["url"] = str(request.url)
            return httpx.Response(200, json={"name": "eduardo"})

        _cliente(handler, site=informado).verify()
        assert visto["url"] == "https://cms.evergreenmkt.com.br/wp-json/wp/v2/users/me?context=edit"

    def test_recusa_http_sem_tls(self):
        """Basic Auth em texto claro entrega a senha para qualquer um no
        caminho — e o WordPress só habilita Application Passwords sob HTTPS."""
        with pytest.raises(WordPressError, match="HTTPS"):
            WordPressClient(
                site_url="http://cms.evergreenmkt.com.br",
                username="eduardo",
                app_password="abcd",
            )

    def test_recusa_url_vazia(self):
        with pytest.raises(WordPressError, match="endereço"):
            WordPressClient(site_url="  ", username="eduardo", app_password="abcd")


class TestAutenticacao:
    def test_manda_basic_auth(self):
        visto = {}

        def handler(request):
            visto["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"name": "eduardo"})

        _cliente(handler).verify()
        esperado = base64.b64encode(b"eduardo:abcd EFGH ijkl").decode()
        assert visto["auth"] == f"Basic {esperado}"

    def test_espacos_da_senha_do_wordpress_sao_preservados(self):
        """O WordPress mostra a senha em grupos de quatro ('abcd EFGH ijkl') e
        aceita com ou sem espaço. Quem cola, cola com espaço — remover por
        conta própria seria adivinhar."""
        visto = {}

        def handler(request):
            visto["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"name": "eduardo"})

        _cliente(handler, senha="abcd EFGH ijkl").verify()
        decodificado = base64.b64decode(visto["auth"].removeprefix("Basic ")).decode()
        assert decodificado == "eduardo:abcd EFGH ijkl"


class TestErros:
    @pytest.mark.parametrize(
        "codigo,trecho",
        [
            (401, "Application Password"),
            (403, "permissão"),
            (404, "REST"),
        ],
    )
    def test_traduz_o_codigo_para_o_que_fazer(self, codigo, trecho):
        """"401" não diz a ninguém o que corrigir. A mensagem tem que apontar
        para a ação."""

        def handler(_request):
            return httpx.Response(codigo, json={"message": "seja lá o que for"})

        with pytest.raises(WordPressError, match=trecho):
            _cliente(handler).verify()

    def test_a_senha_nunca_aparece_na_mensagem_de_erro(self):
        """Mensagem de erro vai para log, para tela e para o histórico de sync.
        Um segredo que vaza por ali vaza para os três de uma vez."""
        segredo = "abcd EFGH ijkl"

        def handler(_request):
            return httpx.Response(500, text=f"erro cru contendo {segredo} por descuido do servidor")

        with pytest.raises(WordPressError) as erro:
            _cliente(handler, senha=segredo).verify()
        assert segredo not in str(erro.value)

    def test_site_fora_do_ar_vira_mensagem_legivel(self):
        def handler(_request):
            raise httpx.ConnectError("sem rota para o host")

        with pytest.raises(WordPressError, match="não respondeu"):
            _cliente(handler).verify()

    def test_resposta_que_nao_e_json_nao_estoura_parser(self):
        """Plugin de manutenção devolvendo HTML é o caso comum, e um
        JSONDecodeError na tela não ajuda ninguém."""

        def handler(_request):
            return httpx.Response(200, text="<html>Em manutenção</html>")

        with pytest.raises(WordPressError, match="não devolveu JSON"):
            _cliente(handler).verify()


class TestPublicacao:
    def test_cria_post_e_devolve_id_e_link(self):
        visto = {}

        def handler(request):
            visto["metodo"] = request.method
            visto["url"] = str(request.url)
            visto["corpo"] = json.loads(request.read())
            return httpx.Response(
                201,
                json={
                    "id": 42,
                    "link": "https://cms.evergreenmkt.com.br/?p=42",
                    "status": "draft",
                },
            )

        resultado = _cliente(handler).create_post({"title": "Oi", "status": "draft"})
        assert visto["metodo"] == "POST"
        assert visto["url"].endswith("/wp-json/wp/v2/posts")
        assert visto["corpo"] == {"title": "Oi", "status": "draft"}
        assert resultado == {
            "id": 42,
            "link": "https://cms.evergreenmkt.com.br/?p=42",
            "status": "draft",
        }

    def test_erro_do_wordpress_carrega_a_mensagem_dele(self):
        """O WordPress explica bem os próprios erros de validação. Trocar isso
        por texto genérico nosso perderia a única informação útil."""

        def handler(_request):
            return httpx.Response(400, json={"message": "O slug informado já está em uso."})

        with pytest.raises(WordPressError, match="slug informado já está em uso"):
            _cliente(handler).create_post({"title": "Oi"})

    def test_resposta_sem_id_nao_e_tratada_como_sucesso(self):
        """200 com corpo estranho é o pior caso: a tela diria 'publicado' e não
        haveria post nenhum. Foi exatamente o que o botão de sync fazia."""

        def handler(_request):
            return httpx.Response(200, json={"ok": True})

        with pytest.raises(WordPressError, match="sem identificar o post"):
            _cliente(handler).create_post({"title": "Oi"})


class TestAtualizacao:
    """WordPress atualiza com POST /posts/{id}, nao PUT (doc oficial)."""

    def test_atualiza_o_post_existente(self):
        visto = {}

        def handler(request):
            visto["metodo"] = request.method
            visto["url"] = str(request.url)
            return httpx.Response(200, json={"id": 42, "link": "https://ex.com/?p=42", "status": "publish"})

        resultado = _cliente(handler).update_post(42, {"title": "Novo titulo"})
        assert visto["metodo"] == "POST"
        assert visto["url"].endswith("/wp-json/wp/v2/posts/42")
        assert resultado["id"] == 42

    def test_post_que_sumiu_do_site_da_erro_legivel(self):
        """Alguem apagou o post pelo painel do WordPress. A mensagem tem que
        dizer isso, nao devolver 404 cru."""

        def handler(_request):
            return httpx.Response(404, json={"code": "rest_post_invalid_id"})

        with pytest.raises(WordPressError, match="nao foi encontrado|não foi encontrado"):
            _cliente(handler).update_post(42, {"title": "x"})


class TestListagem:
    def test_lista_pedindo_todos_os_status(self):
        """O padrao do WordPress e listar SO `publish`. Gerenciar o blog de
        dentro do Bioma sem ver rascunho e agendado seria ver metade."""
        visto = {}

        def handler(request):
            visto["url"] = str(request.url)
            return httpx.Response(200, json=[{"id": 1, "title": {"rendered": "Um"}}])

        _cliente(handler).list_posts()
        assert "status=publish%2Cfuture%2Cdraft%2Cpending%2Cprivate" in visto["url"]
        assert "context=edit" in visto["url"]

    def test_repassa_busca_e_pagina(self):
        visto = {}

        def handler(request):
            visto["url"] = str(request.url)
            return httpx.Response(200, json=[])

        _cliente(handler).list_posts(search="google ads", page=3, per_page=50)
        assert "search=google+ads" in visto["url"] or "search=google%20ads" in visto["url"]
        assert "page=3" in visto["url"]
        assert "per_page=50" in visto["url"]

    def test_achata_os_campos_renderizados(self):
        """WordPress devolve title/excerpt como {"rendered": "..."}. Deixar o
        dicionario cru vazaria a forma do WP para dentro do Bioma e para a tela."""

        def handler(_request):
            return httpx.Response(
                200,
                json=[{
                    "id": 7,
                    "title": {"rendered": "Quanto custa"},
                    "excerpt": {"rendered": "<p>resumo</p>"},
                    "status": "draft",
                    "link": "https://ex.com/?p=7",
                    "date_gmt": "2026-08-20T10:00:00",
                    "modified_gmt": "2026-08-21T10:00:00",
                }],
                headers={"X-WP-Total": "31", "X-WP-TotalPages": "4"},
            )

        resultado = _cliente(handler).list_posts()
        item = resultado["items"][0]
        assert item["title"] == "Quanto custa"
        assert item["excerpt"] == "resumo", "o HTML do resumo tem que sair"
        assert item["status"] == "draft"
        assert resultado["total"] == 31
        assert resultado["total_pages"] == 4

    def test_sem_cabecalho_de_total_nao_inventa_numero(self):
        """Cache e proxy as vezes comem o X-WP-Total. Chutar o total faria a
        paginacao mentir; None diz 'nao sei', que e verdade."""

        def handler(_request):
            return httpx.Response(200, json=[{"id": 1, "title": {"rendered": "Um"}}])

        resultado = _cliente(handler).list_posts()
        assert resultado["total"] is None
        assert resultado["total_pages"] is None


class TestLixeira:
    def test_manda_para_a_lixeira_sem_forcar(self):
        """Sem `force`: o post vai para a lixeira e da para restaurar pelo
        painel. Apagar de vez o conteudo do CLIENTE nao e decisao nossa."""
        visto = {}

        def handler(request):
            visto["metodo"] = request.method
            visto["url"] = str(request.url)
            return httpx.Response(200, json={"deleted": True, "previous": {"id": 42}})

        _cliente(handler).trash_post(42)
        assert visto["metodo"] == "DELETE"
        assert visto["url"].endswith("/wp-json/wp/v2/posts/42")
        assert "force" not in visto["url"], "forcar apagaria sem volta"
