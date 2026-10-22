import pytest
from unittest.mock import patch, MagicMock

from bioma_api.services.seo_geo import run_live_audit


def test_run_live_audit_complete_site():
    mock_html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
      <head>
        <title>EverGreen Agency | Growth e Engenharia Digital</title>
        <meta name="description" content="Agência especializada em growth marketing, engenharia de software e inteligência artificial para escalar operações corporativas com autoridade.">
        <link rel="canonical" href="https://evergreen.com.br/">
        <meta property="og:title" content="EverGreen Agency | Growth e IA">
        <meta property="og:description" content="Escala de operações com engenharia e marketing.">
        <meta property="og:image" content="https://evergreen.com.br/assets/og-image.jpg">
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "EverGreen Agency",
          "url": "https://evergreen.com.br"
        }
        </script>
      </head>
      <body>
        <header>
          <a href="/sobre">Sobre Nós</a>
          <a href="/contato">Contato</a>
          <a href="/privacidade">Privacidade</a>
        </header>
        <main>
          <h1>Transformação Digital e Growth para Empresas</h1>
          <h2>Metodologias Validadas</h2>
          <p>Oferecemos soluções completas de ponta a ponta.</p>
          <img src="/img/logo.png" alt="Logotipo EverGreen Agency">
          <section id="faq">
            <h2>Perguntas Frequentes (FAQ)</h2>
            <p><strong>Como funciona a operação?</strong> Trabalhamos em squads dedicados com sprints semanais.</p>
          </section>
        </main>
      </body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"server": "nginx"}
    mock_resp.text = mock_html

    with patch("httpx.Client.get", return_value=mock_resp):
        audit = run_live_audit("https://evergreen.com.br")

        assert audit["seo_score"] >= 90.0
        assert audit["page_title"] == "EverGreen Agency | Growth e Engenharia Digital"
        assert audit["technical_audit"]["h1_tags"] == ["Transformação Digital e Growth para Empresas"]
        assert audit["technical_audit"]["canonical"] == "https://evergreen.com.br/"
        assert audit["technical_audit"]["images_missing_alt"] == 0

        # GEO & AI Readiness
        assert "Organization" in audit["geo_audit"]["schemas_detected"]
        assert audit["geo_audit"]["eeat_signals"]["has_author_or_team"] is True
        assert audit["geo_audit"]["eeat_signals"]["has_contact_page"] is True
        assert audit["geo_audit"]["faq_count"] >= 1

        # Gerador llms.txt & Schema
        assert "# EverGreen Agency" in audit["generated_llms_txt"]
        assert "ChatGPT" in audit["generated_llms_txt"]
        assert audit["generated_schema_jsonld"]["@type"] == "Organization"


def test_run_live_audit_detects_gaps_on_poor_site():
    mock_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Curto</title>
      </head>
      <body>
        <p>Site sem H1, sem meta description e com imagem sem alt</p>
        <img src="foto.jpg">
      </body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {}
    mock_resp.text = mock_html

    with patch("httpx.Client.get", return_value=mock_resp):
        audit = run_live_audit("https://site-ruim.com.br")

        assert audit["seo_score"] < 50.0
        assert audit["geo_score"] < 40.0
        assert audit["technical_audit"]["images_missing_alt"] == 1
        assert len(audit["technical_audit"]["h1_tags"]) == 0
        assert len(audit["geo_audit"]["schemas_detected"]) == 0
