import pytest
from unittest.mock import patch, MagicMock

from bioma_api.worker_bridge import _ensure_worker_in_path
_ensure_worker_in_path()

from bioma_worker.local_radar import enrich_prospect_website


def test_enrich_prospect_website_empty_or_none():
    res_none = enrich_prospect_website(None)
    assert res_none["crawler_status"] == "no_website"
    assert res_none["emails"] == []
    assert res_none["social_links"] == {}

    res_empty = enrich_prospect_website("   ")
    assert res_empty["crawler_status"] == "no_website"


def test_enrich_prospect_website_extracts_clean_emails_and_socials():
    mock_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Clínica Odonto Exemplo</title>
        <link rel="stylesheet" href="assets/style@2x.png">
      </head>
      <body>
        <h1>Bem-vindo à Clínica Odonto</h1>
        <p>Fale conosco: contato@odontoexemplo.com.br ou suporte@odontoexemplo.com.br</p>
        <!-- Falsos positivos que devem ser descartados -->
        <p>Imagem: banner_logo@2x.png</p>
        <p>Template: support@wixpress.com e developer@sentry.io</p>
        <footer>
          <a href="https://www.instagram.com/odontoexemplo/">Instagram Oficial</a>
          <a href="https://facebook.com/odontoexemplo">Facebook</a>
          <a href="https://www.linkedin.com/company/odonto-exemplo">LinkedIn</a>
          <a href="https://wa.me/5511999998888">Fale no WhatsApp</a>
          <!-- Link social que deve ser ignorado por ser rota interna -->
          <a href="https://instagram.com/explore/">Explore</a>
        </footer>
      </body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html

    with patch("httpx.Client.get", return_value=mock_resp):
        res = enrich_prospect_website("https://odontoexemplo.com.br")
        assert res["crawler_status"] == "completed"
        # E-mails válidos encontrados e falsos positivos descartados
        assert "contato@odontoexemplo.com.br" in res["emails"]
        assert "suporte@odontoexemplo.com.br" in res["emails"]
        assert not any("wixpress.com" in e for e in res["emails"])
        assert not any("sentry.io" in e for e in res["emails"])
        assert not any(".png" in e for e in res["emails"])

        # Redes sociais
        assert res["social_links"].get("instagram") == "https://instagram.com/odontoexemplo"
        assert res["social_links"].get("facebook") == "https://facebook.com/odontoexemplo"
        assert res["social_links"].get("linkedin") == "https://linkedin.com/company/odonto-exemplo"
        assert res["social_links"].get("whatsapp_link") == "https://wa.me/5511999998888"


def test_enrich_prospect_website_timeout_handling():
    import httpx

    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Read timed out")):
        res = enrich_prospect_website("https://site-lento-que-trava.com.br")
        assert res["crawler_status"] == "failed"
        assert "timeout" in res["crawler_error"].lower()
        assert res["emails"] == []
