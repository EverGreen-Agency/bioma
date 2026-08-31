import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

# Feeds RSS públicos de vagas remotas / freelancers
DEFAULT_RSS_SOURCES = [
    {
        "platform": "weworkremotely",
        "name": "WeWorkRemotely - Marketing & Sales",
        "url": "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
    },
    {
        "platform": "weworkremotely",
        "name": "WeWorkRemotely - Full Stack & Tech",
        "url": "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    },
    {
        "platform": "remotive",
        "name": "Remotive - All Remote Jobs",
        "url": "https://remotive.com/remote-jobs/feed",
    },
    {
        "platform": "freelancer",
        "name": "Freelancer.com - Brasil",
        "url": "https://www.freelancer.com.br/rss.xml",
    },
]

def _strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    return " ".join(clean.split())

def fetch_rss_opportunities(custom_sources: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    sources_to_fetch = list(DEFAULT_RSS_SOURCES)
    if custom_sources:
        for cs in custom_sources:
            if cs.get("url"):
                sources_to_fetch.append(cs)

    opportunities = []
    seen_urls = set()

    for source in sources_to_fetch:
        try:
            req = urllib.request.Request(
                source["url"],
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)

                for item in root.findall(".//item"):
                    title = item.findtext("title") or "Projeto Sem Título"
                    link = item.findtext("link") or ""
                    description = item.findtext("description") or ""

                    title_clean = _strip_html(title).strip()
                    link_clean = link.strip()
                    desc_clean = _strip_html(description).strip()[:1000]

                    if link_clean and link_clean in seen_urls:
                        continue
                    if link_clean:
                        seen_urls.add(link_clean)

                    opportunities.append({
                        "source_platform": source["platform"],
                        "title": title_clean,
                        "url": link_clean or None,
                        "description": desc_clean or "Descrição disponível na plataforma.",
                        "budget_text": "A combinar (RSS)",
                        "raw_payload": {"source_name": source["name"]},
                    })
        except Exception as exc:
            print(f"[Worker Scraper] Erro ao ler RSS {source.get('name', 'Fonte')}: {exc}")

    return opportunities
