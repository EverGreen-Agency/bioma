"""Extracao deterministica e nao executavel de documentos HTML de projeto.

O parser nunca renderiza nem executa scripts do arquivo. Ele reconhece o
contrato semantico mais comum nos prototipos da EG (articles com data-* e uma
linha do tempo) e preserva trechos como evidencia para revisao humana.
"""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from html.parser import HTMLParser
import re
import unicodedata


EXTRACTION_VERSION = "html-project-v1"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _fold(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    )


class _ProjectHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.title: str | None = None
        self.all_text: list[str] = []
        self.article: dict | None = None
        self.articles: list[dict] = []
        self.timeline: dict | None = None
        self.timelines: list[dict] = []
        self.captures: list[dict] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        if tag in {"style", "script", "noscript", "svg"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        classes = set(attrs.get("class", "").split())
        if tag == "article" and self.article is None:
            self.article = {"attrs": attrs, "text": [], "links": []}
        if self.article is not None:
            if tag == "h3":
                self.captures.append({"tag": tag, "key": "title", "text": [], "owner": "article"})
            for key in ("desc", "action", "trade", "meta"):
                if key in classes:
                    self.captures.append({"tag": tag, "key": key, "text": [], "owner": "article"})
            if tag == "a" and attrs.get("href"):
                self.article["links"].append(attrs["href"])
            if tag == "option" and "selected" in attrs:
                self.captures.append({"tag": tag, "key": "tracker_status", "text": [], "owner": "article"})
        if tag == "div" and "t" in classes and self.article is None:
            self.timeline = {"text": [], "date_label": ""}
            self.captures.append({"tag": tag, "key": "timeline", "text": [], "owner": "timeline"})
        if self.timeline is not None and tag == "b":
            self.captures.append({"tag": tag, "key": "date_label", "text": [], "owner": "timeline"})
        if tag == "h1" and self.title is None:
            self.captures.append({"tag": tag, "key": "document_title", "text": [], "owner": "document"})

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        for index in range(len(self.captures) - 1, -1, -1):
            capture = self.captures[index]
            if capture["tag"] != tag:
                continue
            value = _clean(" ".join(capture["text"]))
            self.captures.pop(index)
            if capture["owner"] == "article" and self.article is not None:
                self.article[capture["key"]] = value
            elif capture["owner"] == "timeline" and self.timeline is not None:
                self.timeline[capture["key"]] = value
            elif capture["owner"] == "document" and value:
                self.title = value
            break
        if tag == "article" and self.article is not None:
            self.article["text"] = _clean(" ".join(self.article["text"]))
            self.articles.append(self.article)
            self.article = None
        if tag == "div" and self.timeline is not None:
            value = _clean(" ".join(self.timeline["text"]))
            if value and self.timeline.get("date_label"):
                self.timeline["text"] = value
                self.timelines.append(self.timeline)
            self.timeline = None
            self.captures = [item for item in self.captures if item["owner"] != "timeline"]

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not data.strip():
            return
        value = _clean(data)
        self.all_text.append(value)
        if self.article is not None:
            self.article["text"].append(value)
        if self.timeline is not None:
            self.timeline["text"].append(value)
        for capture in self.captures:
            capture["text"].append(value)


MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _dates_from_label(label: str, default_year: int) -> tuple[date | None, date | None]:
    folded = _fold(label).replace("–", "-").replace("—", "-")
    quarter = re.search(r"q([1-4])\s*-\s*q([1-4])\s+(20\d{2})", folded)
    if quarter:
        start_q, end_q, year = map(int, quarter.groups())
        start_month = (start_q - 1) * 3 + 1
        end_month = end_q * 3
        end_day = 31 if end_month in {1, 3, 5, 7, 8, 10, 12} else 30
        return date(year, start_month, 1), date(year, end_month, end_day)
    match = re.search(r"(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s+([a-z]{3})\w*(?:\s+(20\d{2}))?", folded)
    if match and match.group(3) in MONTHS:
        first, last, month, year = match.groups()
        resolved_year = int(year or default_year)
        return date(resolved_year, MONTHS[month], int(first)), date(resolved_year, MONTHS[month], int(last or first))
    month_match = re.search(r"\b([a-z]{3})\w*\s+(20\d{2})\b", folded)
    if month_match and month_match.group(1) in MONTHS:
        month = MONTHS[month_match.group(1)]
        year = int(month_match.group(2))
        next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        from datetime import timedelta
        return date(year, month, 1), next_month - timedelta(days=1)
    return None, None


def _priority(value: str) -> str:
    normalized = value.upper().replace(" ", "")
    if normalized == "P0":
        return "critical"
    if normalized in {"P0/P1", "P0P1"}:
        return "high"
    if normalized == "P1":
        return "high"
    if normalized == "P2":
        return "low"
    return "medium"


def _candidate_id(kind: str, title: str, end_at: date | None) -> str:
    digest = sha256(f"{kind}|{title}|{end_at or ''}".encode("utf-8")).hexdigest()[:16]
    return f"{kind}-{digest}"


def extract_project_html(content: str) -> dict:
    parser = _ProjectHtmlParser()
    parser.feed(content)
    document_text = _clean(" ".join(parser.all_text))[:200_000]
    years = [int(value) for value in re.findall(r"\b20\d{2}\b", parser.title or document_text[:2_000])]
    default_year = min(years) if years else date.today().year
    candidates: list[dict] = []

    for article in parser.articles:
        attrs = article["attrs"]
        title = _clean(article.get("title") or "")
        if not title:
            continue
        deadline = None
        if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", attrs.get("data-deadline", "")):
            deadline = date.fromisoformat(attrs["data-deadline"])
        summary_parts = [article.get("desc"), article.get("trade")]
        summary = _clean(" ".join(part for part in summary_parts if part)) or article["text"][:2_000]
        action = _clean(article.get("action") or "") or None
        metadata = {
            "source_kind": attrs.get("data-kind") or None,
            "timing": attrs.get("data-timing") or None,
            "tracker_status": article.get("tracker_status") or None,
            "source_url": article["links"][0] if article["links"] else None,
            "trade_off": article.get("trade") or None,
            "suggested_action": action,
            "deadline_source": attrs.get("data-deadline") or None,
        }
        candidates.append({
            "id": _candidate_id("opportunity_event", title, deadline),
            "kind": "opportunity_event",
            "title": title[:300],
            "summary": summary[:20_000] or None,
            "priority": _priority(attrs.get("data-priority", "")),
            "backlog_status": "candidate",
            "acceptance_criteria": action[:20_000] if action else None,
            "definition_of_done": None,
            "planned_start_at": None,
            "planned_end_at": deadline,
            "source_excerpt": article["text"][:4_000],
            "metadata": {key: value for key, value in metadata.items() if value is not None},
        })

    for timeline in parser.timelines:
        label = timeline["date_label"]
        start_at, end_at = _dates_from_label(label, default_year)
        text = timeline["text"]
        title = _clean(text.removeprefix(label).lstrip(" ·:-")) or text
        candidates.append({
            "id": _candidate_id("milestone", title, end_at),
            "kind": "milestone",
            "title": title[:300],
            "summary": text[:20_000],
            "priority": "medium",
            "backlog_status": "candidate",
            "acceptance_criteria": None,
            "definition_of_done": None,
            "planned_start_at": start_at,
            "planned_end_at": end_at,
            "source_excerpt": text[:4_000],
            "metadata": {"date_label": label},
        })

    deduplicated = {candidate["id"]: candidate for candidate in candidates}
    warnings: list[str] = []
    if not deduplicated:
        warnings.append("Nenhum card estruturado ou marco de linha do tempo foi reconhecido; revise o documento manualmente.")
    if any(item["planned_end_at"] is None for item in deduplicated.values()):
        warnings.append("Alguns itens não possuem uma data exata e permanecem sem vencimento até revisão.")
    return {
        "title": parser.title,
        "text": document_text,
        "candidates": list(deduplicated.values()),
        "warnings": warnings,
    }
