"""Pesquisa de plataforma para decisão build vs. buy.

O que este módulo NÃO faz, e por quê: não cria conta, não faz login, não usa o
produto. Testar de verdade uma SaaS exige cadastro, muitas vezes cartão, e os
termos de uso da maioria proíbem acesso automatizado autenticado. Fingir que um
robô "testou" 78 plataformas produziria 78 opiniões confiantes sobre nada.

O que ele faz: busca as páginas públicas (home, preços, sobre), extrai o texto
de verdade, e pede ao modelo uma leitura estruturada com a pergunta certa —
"isto substitui o Bioma?" — devolvendo as URLs que realmente foram lidas. O
teste com as mãos continua sendo humano; o que sai daqui é a **fila de
prioridade** de quem merece essa tarde.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
import json
import re

import httpx

# Caminhos que quase toda SaaS usa para as duas páginas que decidem: o que custa
# e o que faz. Tentados em ordem; o que não existir é ignorado sem erro.
CANDIDATE_PATHS = ["", "/pricing", "/precos", "/planos", "/product", "/about"]

MAX_CHARS_PER_PAGE = 12_000
MAX_TOTAL_CHARS = 30_000

INSTRUCTIONS = """Você analisa plataformas de software para uma agência brasileira (EverGreen)
que está construindo um produto próprio chamado Bioma.

Sua tarefa é responder a UMA pergunta de negócio: o que a EverGreen deveria fazer
com esta plataforma?

Regras que não se negociam:
- Baseie-se APENAS no texto das páginas fornecidas. Se a informação não está lá,
  diga que não está — não complete com o que você acha que sabe sobre a empresa.
- Preço: só relate o que estiver escrito. "Não informado na página" é resposta
  válida e útil. Nunca estime valor.
- `overlap_score` é o quanto do que esta plataforma faz o Bioma já faz ou
  pretende fazer, com base na lista de features do Bioma fornecida. Alta
  sobreposição não é ruim por si: é o sinal de que vale comparar a sério.
- `threat_level` responde: esta plataforma é motivo para a EverGreen PARAR de
  construir a parte correspondente do Bioma? `critica` significa "faz melhor
  exatamente o que o Bioma se propõe a fazer, e é comprável hoje".
- Seja específico e curto. "Plataforma robusta e moderna" não ajuda ninguém a
  decidir nada."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "name", "category", "one_liner", "pricing_summary", "what_it_does",
        "who_its_for", "has_that_bioma_lacks", "bioma_has_that_it_lacks",
        "overlap_score", "threat_level", "recommended_verdict", "verdict_reason",
        "worth_hands_on_test", "open_questions",
    ],
    "properties": {
        "name": {"type": "string"},
        "category": {"type": "string"},
        "one_liner": {"type": "string"},
        "pricing_summary": {"type": "string"},
        "what_it_does": {"type": "array", "items": {"type": "string"}},
        "who_its_for": {"type": "string"},
        "has_that_bioma_lacks": {"type": "array", "items": {"type": "string"}},
        "bioma_has_that_it_lacks": {"type": "array", "items": {"type": "string"}},
        "overlap_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "threat_level": {"type": "string", "enum": ["nenhuma", "baixa", "media", "alta", "critica"]},
        "recommended_verdict": {
            "type": "string",
            "enum": ["assinar", "integrar", "absorver", "comprar", "monitorar", "descartar", "repensar"],
        },
        "verdict_reason": {"type": "string"},
        "worth_hands_on_test": {"type": "boolean"},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
}


class _TextExtractor(HTMLParser):
    """Texto visível + og:image, sem dependência nova.

    `bs4` resolveria em três linhas, mas é uma dependência a mais no worker para
    um trabalho que a stdlib faz. Script, style e nav saem porque são ruído que
    empurraria o conteúdo real para fora do limite de caracteres.
    """

    SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.preview_image: str | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1
        if tag == "meta":
            attributes = dict(attrs)
            prop = (attributes.get("property") or attributes.get("name") or "").lower()
            if prop in ("og:image", "twitter:image") and not self.preview_image:
                self.preview_image = attributes.get("content")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts))


def fetch_pages(url: str, http_client: httpx.Client | None = None) -> dict[str, Any]:
    """Busca as páginas públicas. Devolve só o que respondeu 200 de verdade."""
    base = url if url.startswith("http") else f"https://{url}"
    owns_client = http_client is None
    client = http_client or httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        headers={
            # Identificação honesta: quem olhar o log do servidor sabe quem passou.
            "User-Agent": "BiomaPlatformStudy/1.0 (+https://evergreengrowth.com.br; avaliacao de ferramentas)",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    )
    pages: list[dict[str, str]] = []
    preview_image: str | None = None
    errors: list[str] = []
    try:
        for path in CANDIDATE_PATHS:
            target = urljoin(base, path) if path else base
            try:
                response = client.get(target)
            except Exception as exc:
                errors.append(f"{target}: {type(exc).__name__}")
                continue
            if response.status_code != 200:
                continue
            if "text/html" not in response.headers.get("content-type", ""):
                continue
            parser = _TextExtractor()
            try:
                parser.feed(response.text)
            except Exception:
                continue
            text = parser.text[:MAX_CHARS_PER_PAGE]
            if len(text) < 120:
                # Página que só carrega JavaScript não tem texto para ler. Melhor
                # deixar de fora do que mandar "Loading..." como conteúdo.
                continue
            if parser.preview_image and not preview_image:
                preview_image = urljoin(response.url and str(response.url) or target, parser.preview_image)
            pages.append({"url": str(response.url), "text": text})
            if sum(len(page["text"]) for page in pages) >= MAX_TOTAL_CHARS:
                break
    finally:
        if owns_client:
            client.close()

    return {"pages": pages, "preview_image": preview_image, "errors": errors}


def analyze(request: dict[str, Any], settings, http_client: httpx.Client | None = None) -> dict[str, Any]:
    """Busca as páginas e pede a leitura estruturada ao modelo.

    Sem `OPENAI_API_KEY` NÃO devolve prévia: uma análise de build-vs-buy inventada
    localmente seria pior que nenhuma — daria a mesma cara de resposta pronta para
    uma decisão de "continuo construindo o Bioma?". Falha alto.
    """
    url = request["url"]
    fetched = fetch_pages(url, http_client=http_client)
    if not fetched["pages"]:
        raise RuntimeError(
            f"Nenhuma página pública legível em {url}. "
            f"Site pode exigir JavaScript ou bloquear acesso automatizado. "
            f"Tentativas: {', '.join(fetched['errors']) or 'todas responderam sem conteúdo'}"
        )

    if not settings.openai_api_key:
        raise RuntimeError(
            "Análise de plataforma exige OPENAI_API_KEY: esta decisão não aceita prévia local."
        )

    payload = {
        "model": settings.openai_model,
        "instructions": INSTRUCTIONS,
        "input": json.dumps(
            {
                "platform_url": url,
                "evaluating_for": request.get("targets") or ["bioma"],
                "bioma_features": request.get("bioma_features") or [],
                "pages": fetched["pages"],
            },
            ensure_ascii=False,
            default=str,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bioma_platform_study",
                "strict": True,
                "schema": SCHEMA,
            }
        },
        "max_output_tokens": 2000,
        "store": False,
    }

    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    owns_client = http_client is None
    client = http_client or httpx.Client(
        base_url="https://api.openai.com", timeout=settings.openai_request_timeout_seconds
    )
    try:
        response = client.post("/v1/responses", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
    finally:
        if owns_client:
            client.close()

    output = json.loads(_output_text(response_data))
    usage = response_data.get("usage") or {}
    return {
        "output": output,
        "sources": [page["url"] for page in fetched["pages"]],
        "preview_image": fetched["preview_image"],
        "generation_mode": "live",
        "provider": "openai",
        "model": settings.openai_model,
        "usage": {
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
        },
    }


def _output_text(response_data: dict[str, Any]) -> str:
    for item in response_data.get("output", []):
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text":
                return content["text"]
    raise RuntimeError("Resposta do modelo sem texto estruturado.")


def derive_name(url: str) -> str:
    """Nome legível a partir do domínio, até a pesquisa achar o nome real."""
    host = urlparse(url if url.startswith("http") else f"https://{url}").netloc
    host = host.removeprefix("www.")
    root = host.split(".")[0]
    return root.replace("-", " ").title() if root else url


def test_priority(overlap_score: int | None, threat_level: str | None, worth_test: bool) -> int:
    """Ordem da fila de teste manual.

    Sobreposição alta com ameaça alta vai primeiro: é a plataforma que pode
    responder "pare de construir isso", e essa resposta vale mais cedo do que
    tarde. Plataforma que não vale a mão fica no fim, mas continua na lista.
    """
    threat_weight = {"critica": 50, "alta": 35, "media": 20, "baixa": 8, "nenhuma": 0}
    score = (overlap_score or 0) // 2
    score += threat_weight.get(threat_level or "nenhuma", 0)
    if worth_test:
        score += 15
    return min(100, score)
