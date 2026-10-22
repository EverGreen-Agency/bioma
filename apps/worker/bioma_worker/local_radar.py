"""Radar Local: busca negócios locais no Google Places e audita presença digital.

Duas etapas independentes:
1. search_local_businesses — Places API (New) Text Search. Sem GOOGLE_PLACES_API_KEY
   a função FALHA ALTO: inventar negócios locais em modo prévia seria fabricar dado.
2. audit_local_prospect — diagnóstico consultivo. Sem OPENAI_API_KEY cai para uma
   prévia determinística construída SÓ com os campos reais coletados do Places,
   rotulada como preview.
"""

import json
from typing import Any

import httpx

PLACES_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

# Só os campos que realmente usamos; o FieldMask é obrigatório na API New e
# define o SKU cobrado (rating/website/phone são tier Enterprise).
PLACES_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.rating",
        "places.userRatingCount",
        "places.businessStatus",
        "places.types",
        "nextPageToken",
    ]
)

AUDIT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["diagnosis", "opportunities", "suggested_message", "cautions"],
    "properties": {
        "diagnosis": {"type": "string"},
        "opportunities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["issue", "recommended_service", "rationale"],
                "properties": {
                    "issue": {"type": "string"},
                    "recommended_service": {"type": "string"},
                    "rationale": {"type": "string"},
                },
            },
        },
        "suggested_message": {"type": "string"},
        "cautions": {"type": "array", "items": {"type": "string"}},
    },
}

AUDIT_INSTRUCTIONS = """
Você é o auditor de presença digital da EverGreen, agência de growth e marketing.
Receberá os dados REAIS de um negócio local coletados do Google Maps (nome,
endereço, telefone, site, nota, quantidade de avaliações, status e lacunas já
calculadas). Produza um diagnóstico consultivo e uma mensagem de abordagem.

Regras obrigatórias:
- use APENAS os campos fornecidos; não invente fatos sobre o negócio (não afirme
  que ele anuncia, que o site é ruim, ou qualquer coisa não observada nos dados);
- se um campo estiver ausente, trate a ausência como a observação (ex.: "não
  encontramos site cadastrado no Google"), nunca como defeito presumido;
- a mensagem deve ser em português do Brasil, curta (máx. 500 caracteres),
  consultiva, identificando a EverGreen, citando 1-2 observações concretas e
  fechando com convite leve para conversa — sem promessa de resultado;
- se receber sector_playbook (playbook de prospecção do setor, vindo da pesquisa
  de mercado da EverGreen), use os ângulos de abertura e respeite os cuidados de
  credibilidade ao redigir a mensagem — mas nunca cite um fato do playbook como
  se fosse uma observação sobre ESTE negócio específico;
- em cautions, liste o que um humano deve conferir antes de enviar.
""".strip()


def search_local_businesses(
    request: dict[str, Any],
    settings,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    api_key = settings.google_places_api_key
    if not api_key:
        raise RuntimeError(
            "GOOGLE_PLACES_API_KEY não configurada no worker. O Radar Local não roda "
            "em modo prévia porque os negócios retornados seriam inventados."
        )

    niche = request["niche"].strip()
    city = request["city"].strip()
    limit = min(int(request.get("limit") or 20), 60)
    query_text = f"{niche} em {city}"

    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": PLACES_FIELD_MASK,
        "Content-Type": "application/json",
    }

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=settings.google_request_timeout_seconds)
    places: list[dict[str, Any]] = []
    try:
        page_token: str | None = None
        while len(places) < limit:
            body: dict[str, Any] = {
                "textQuery": query_text,
                "pageSize": min(limit - len(places), 20),
                "languageCode": "pt-BR",
                "regionCode": "BR",
            }
            if page_token:
                body["pageToken"] = page_token
            response = client.post(PLACES_ENDPOINT, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()
            places.extend(payload.get("places", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
    finally:
        if owns_client:
            client.close()

    prospects = [_prospect_row(place) for place in places[:limit]]
    return {"query_text": query_text, "prospects": prospects}


def _prospect_row(place: dict[str, Any]) -> dict[str, Any]:
    rating = place.get("rating")
    rating_count = place.get("userRatingCount")
    row = {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text") or "Sem nome",
        "address": place.get("formattedAddress"),
        "phone": place.get("nationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "google_maps_url": place.get("googleMapsUri"),
        "rating": rating,
        "rating_count": rating_count,
        "business_status": place.get("businessStatus"),
        "place_types": place.get("types") or [],
    }
    row["presence_score"], row["presence_gaps"] = _presence_audit(row)
    return row


def _presence_audit(row: dict[str, Any]) -> tuple[int, list[str]]:
    """Score determinístico da presença digital, calculado só dos campos reais."""
    score = 100
    gaps: list[str] = []
    if not row["website"]:
        score -= 35
        gaps.append("Sem site cadastrado no Google")
    if not row["phone"]:
        score -= 15
        gaps.append("Sem telefone cadastrado no Google")
    rating = row["rating"]
    rating_count = row["rating_count"] or 0
    if rating is None:
        score -= 15
        gaps.append("Sem avaliações no Google")
    else:
        if rating_count < 10:
            score -= 15
            gaps.append(f"Poucas avaliações ({rating_count})")
        if float(rating) < 4.0 and rating_count >= 5:
            score -= 20
            gaps.append(f"Nota baixa ({rating})")
    if row["business_status"] and row["business_status"] != "OPERATIONAL":
        gaps.append(f"Status no Google: {row['business_status']}")
    return max(score, 0), gaps


def normalize_imported_prospects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Converte linhas importadas de planilha (scrape manual do Eduardo) para o
    formato de prospect, com o mesmo score determinístico da busca via API.
    Só normaliza o que veio — nunca preenche campo ausente com palpite."""
    import hashlib

    prospects: list[dict[str, Any]] = []
    for raw in rows:
        name = (raw.get("name") or "").strip()
        if not name:
            continue
        address = (raw.get("address") or "").strip() or None
        rating = raw.get("rating")
        rating_count = raw.get("rating_count")
        row = {
            # Import não tem place_id do Google; derivamos um estável de
            # nome+endereço para o diff entre rescans continuar funcionando.
            "place_id": "import-" + hashlib.sha1(f"{name}|{address or ''}".lower().encode()).hexdigest()[:20],
            "name": name,
            "address": address,
            "phone": (raw.get("phone") or "").strip() or None,
            "website": (raw.get("website") or "").strip() or None,
            "google_maps_url": (raw.get("google_maps_url") or "").strip() or None,
            "rating": float(rating) if rating not in (None, "") else None,
            "rating_count": int(rating_count) if rating_count not in (None, "") else None,
            "business_status": None,
            "place_types": [],
        }
        row["presence_score"], row["presence_gaps"] = _presence_audit(row)
        prospects.append(row)
    return prospects


def audit_local_prospect(
    prospect: dict[str, Any],
    settings,
    http_client: httpx.Client | None = None,
    playbook: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "audit": _preview_audit(prospect),
            "suggested_message": _preview_message(prospect),
            "audit_mode": "preview",
        }

    payload = {
        "model": settings.openai_model,
        "instructions": AUDIT_INSTRUCTIONS,
        "input": json.dumps(
            {
                "name": prospect.get("name"),
                "address": prospect.get("address"),
                "phone": prospect.get("phone"),
                "website": prospect.get("website"),
                "rating": prospect.get("rating"),
                "rating_count": prospect.get("rating_count"),
                "business_status": prospect.get("business_status"),
                "presence_score": prospect.get("presence_score"),
                "presence_gaps": prospect.get("presence_gaps") or [],
                "changes_since_last_scan": prospect.get("changes") or [],
                "sector_playbook": playbook,
            },
            ensure_ascii=False,
            default=str,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bioma_local_radar_audit",
                "strict": True,
                "schema": AUDIT_SCHEMA,
            }
        },
        "max_output_tokens": 1200,
        "store": False,
    }

    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    owns_client = http_client is None
    client = http_client or httpx.Client(
        base_url="https://api.openai.com",
        timeout=settings.openai_request_timeout_seconds,
    )
    try:
        response = client.post("/v1/responses", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
    finally:
        if owns_client:
            client.close()

    output = json.loads(_output_text(response_data))
    return {
        "audit": output,
        "suggested_message": output.get("suggested_message") or _preview_message(prospect),
        "audit_mode": "live",
    }


def _output_text(response_data: dict[str, Any]) -> str:
    if isinstance(response_data.get("output_text"), str):
        return response_data["output_text"]
    for item in response_data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise RuntimeError("A resposta do provedor não contém output_text.")


def _preview_audit(prospect: dict[str, Any]) -> dict[str, Any]:
    gaps = prospect.get("presence_gaps") or []
    return {
        "diagnosis": (
            f"Prévia local para {prospect.get('name')}: diagnóstico montado apenas com os "
            "campos coletados do Google Maps, sem análise de IA. "
            f"Lacunas observadas: {', '.join(gaps) if gaps else 'nenhuma detectada nos campos coletados'}."
        ),
        "opportunities": [
            {
                "issue": gap,
                "recommended_service": "A definir por um humano",
                "rationale": "Configure OPENAI_API_KEY para a recomendação consultiva.",
            }
            for gap in gaps
        ],
        "suggested_message": _preview_message(prospect),
        "cautions": [
            "Prévia local determinística — nenhuma análise de IA foi executada.",
            "Confirme os dados no Google Maps antes de qualquer contato.",
        ],
    }


def _preview_message(prospect: dict[str, Any]) -> str:
    name = prospect.get("name") or "sua empresa"
    gaps = prospect.get("presence_gaps") or []
    observation = gaps[0].lower() if gaps else "oportunidades na sua presença no Google"
    return (
        f"Olá! Somos a EverGreen, agência de growth e marketing. Analisando o perfil de "
        f"{name} no Google Maps, notamos {observation}. Faz sentido uma conversa rápida "
        "sobre como fortalecer sua presença digital? Sem compromisso."
    )


DISCARDED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".pdf",
}

DISCARDED_EMAIL_DOMAINS = {
    "wixpress.com", "example.com", "domain.com", "sentry.io",
    "schema.org", "gravatar.com", "wordpress.org", "cloudflare.com",
    "w3.org", "googleapis.com", "github.com", "facebook.com", "instagram.com",
}

DISCARDED_SOCIAL_SLUGS = {
    "p", "reel", "reels", "stories", "explore", "sharer", "share",
    "privacy", "terms", "about", "contact", "home", "intent",
}


def enrich_prospect_website(website_url: str | None, timeout_seconds: float = 7.0) -> dict[str, Any]:
    """Web crawler autônomo (estilo Google Maps Scraper Kit):
    Navega no site do estabelecimento e minera e-mails corporativos e perfis
    sociais (Instagram, Facebook, LinkedIn, WhatsApp link).
    Aplica filtros estritos anti-lixo e resiliência a SSL e timeouts."""
    import re
    from urllib.parse import urljoin, urlparse

    if not website_url or not website_url.strip():
        return {
            "emails": [],
            "social_links": {},
            "crawler_status": "no_website",
            "crawler_error": None,
        }

    raw_url = website_url.strip()
    if not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url

    parsed_base = urlparse(raw_url)
    domain_netloc = parsed_base.netloc.lower()
    clean_domain = domain_netloc.split(":")[0]
    if clean_domain.startswith("www."):
        clean_domain = clean_domain[4:]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    emails_found: set[str] = set()
    socials_found: dict[str, str] = {}

    def extract_from_html(html_text: str):
        # 1. Extração e sanitização estrita de e-mails
        email_matches = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html_text)
        for email in email_matches:
            email_lower = email.strip().lower().rstrip(".,;!?:")
            parts = email_lower.split("@")
            if len(parts) != 2:
                continue
            local_part, email_domain = parts
            if any(email_lower.endswith(ext) for ext in DISCARDED_EXTENSIONS):
                continue
            if email_domain in DISCARDED_EMAIL_DOMAINS:
                continue
            if len(local_part) < 2 or len(email_domain) < 3 or "." not in email_domain:
                continue
            emails_found.add(email_lower)

        # 2. Extração de perfis sociais
        insta_matches = re.findall(r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?', html_text, re.IGNORECASE)
        for user in insta_matches:
            u_clean = user.strip().lower().rstrip("/")
            if u_clean and u_clean not in DISCARDED_SOCIAL_SLUGS and "instagram" not in socials_found:
                socials_found["instagram"] = f"https://instagram.com/{u_clean}"

        fb_matches = re.findall(r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9_.-]+)/?', html_text, re.IGNORECASE)
        for fb in fb_matches:
            f_clean = fb.strip().lower().rstrip("/")
            if f_clean and f_clean not in DISCARDED_SOCIAL_SLUGS and "facebook" not in socials_found:
                socials_found["facebook"] = f"https://facebook.com/{f_clean}"

        li_matches = re.findall(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/([a-zA-Z0-9_.-]+)/?', html_text, re.IGNORECASE)
        for li in li_matches:
            l_clean = li.strip().lower().rstrip("/")
            if l_clean and l_clean not in DISCARDED_SOCIAL_SLUGS and "linkedin" not in socials_found:
                socials_found["linkedin"] = f"https://linkedin.com/company/{l_clean}"

        wa_matches = re.findall(r'https?://(?:api\.whatsapp\.com/send\?phone=|wa\.me/)(\d+)', html_text, re.IGNORECASE)
        for wa in wa_matches:
            if "whatsapp_link" not in socials_found and len(wa) >= 10:
                socials_found["whatsapp_link"] = f"https://wa.me/{wa}"

    try:
        with httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            verify=False,
            headers=headers,
        ) as client:
            resp = client.get(raw_url)
            if resp.status_code < 400:
                extract_from_html(resp.text)

                # Busca de contingência em link de contato caso não encontre e-mails na home
                if not emails_found:
                    contact_match = re.search(
                        r'href=["\']([^"\']*(?:contato|fale-conosco|fale_conosco|atendimento)[^"\']*)["\']',
                        resp.text,
                        re.IGNORECASE,
                    )
                    if contact_match:
                        contact_href = contact_match.group(1)
                        contact_url = urljoin(raw_url, contact_href)
                        if urlparse(contact_url).netloc.lower() == parsed_base.netloc.lower():
                            try:
                                sub_resp = client.get(contact_url)
                                if sub_resp.status_code < 400:
                                    extract_from_html(sub_resp.text)
                            except Exception:
                                pass

            sorted_emails = sorted(
                list(emails_found),
                key=lambda e: (
                    0 if clean_domain and clean_domain in e else 1,
                    0 if any(e.startswith(p) for p in ("contato@", "comercial@", "atendimento@", "vendas@")) else 1,
                    len(e),
                ),
            )

            return {
                "emails": sorted_emails,
                "social_links": socials_found,
                "crawler_status": "completed",
                "crawler_error": None,
            }
    except httpx.TimeoutException:
        return {
            "emails": [],
            "social_links": {},
            "crawler_status": "failed",
            "crawler_error": "Tempo limite esgotado ao acessar o site (timeout)",
        }
    except Exception as exc:
        return {
            "emails": [],
            "social_links": {},
            "crawler_status": "failed",
            "crawler_error": f"Falha de conexão: {str(exc)[:120]}",
        }
