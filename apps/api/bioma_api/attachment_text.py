"""Extração de texto de anexos do copiloto.

Regra que orienta tudo aqui: **o que vira texto funciona em qualquer provedor**.
Um PDF transformado em texto roda no Codex CLI, na cota da assinatura, sem
precisar de modelo com visão. Por isso extraímos sempre que dá, e só recorremos
a capacidade especial (visão, transcrição) quando não há texto para extrair.

Quando não dá, dizemos qual foi o motivo. "Não deu para ler" é informação: PDF
escaneado sem OCR, planilha binária e .zip são três situações diferentes, e
quem anexou precisa saber qual antes de perguntar "o que você achou do arquivo?".
"""

from __future__ import annotations

import csv
import io
import json

# Limite por anexo. Um PDF de 80 páginas sozinho ocuparia todo o contexto e
# empurraria para fora o dossiê — que é o que o copiloto sabe sobre a operação.
MAX_CHARS = 20_000

TEXT_TYPES = {
    "text/plain", "text/markdown", "text/csv", "text/tab-separated-values",
    "application/json", "text/html", "text/xml", "application/xml",
    "application/x-yaml", "text/yaml",
}
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
AUDIO_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/webm",
    "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/ogg",
}
PDF_TYPE = "application/pdf"


def classify(content_type: str, file_name: str) -> str:
    """image | audio | document — decide como o conteúdo chega ao modelo."""
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized in IMAGE_TYPES or normalized.startswith("image/"):
        return "image"
    if normalized in AUDIO_TYPES or normalized.startswith("audio/"):
        return "audio"
    return "document"


def extract(content: bytes, content_type: str, file_name: str) -> dict:
    """Devolve `{status, text, error, truncated_chars}`.

    Nunca levanta: anexo ilegível não pode derrubar o envio da mensagem. O
    usuário perde a leitura daquele arquivo, não a conversa.
    """
    normalized = (content_type or "").split(";")[0].strip().lower()
    kind = classify(content_type, file_name)

    if kind == "image":
        # Imagem não tem texto para extrair — vai para um modelo com visão.
        return _result("not_needed", None, None)
    if kind == "audio":
        # Transcrição acontece depois, num passo próprio (precisa de provedor).
        return _result("pending", None, None)

    try:
        if normalized == PDF_TYPE or file_name.lower().endswith(".pdf"):
            return _pdf(content)
        if normalized == "text/csv" or file_name.lower().endswith((".csv", ".tsv")):
            return _csv(content, delimiter="\t" if file_name.lower().endswith(".tsv") else ",")
        if normalized == "application/json" or file_name.lower().endswith(".json"):
            return _json(content)
        if normalized in TEXT_TYPES or _looks_like_text(content):
            return _truncate(content.decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001 — ver docstring
        return _result("failed", None, f"{type(exc).__name__}: {exc}"[:500])

    return _result(
        "unsupported",
        None,
        f"Tipo {normalized or 'desconhecido'} não tem extração de texto. "
        "O arquivo fica guardado, mas o copiloto não consegue ler o conteúdo.",
    )


def _result(status: str, text: str | None, error: str | None, truncated: int | None = None) -> dict:
    return {"status": status, "text": text, "error": error, "truncated_chars": truncated}


def _truncate(text: str) -> dict:
    clean = text.strip()
    if len(clean) <= MAX_CHARS:
        return _result("extracted", clean, None, 0)
    return _result("extracted", clean[:MAX_CHARS], None, len(clean) - MAX_CHARS)


def _looks_like_text(content: bytes) -> bool:
    """Heurística para arquivo sem content-type confiável.

    Navegador manda `application/octet-stream` para extensão que não conhece.
    Byte nulo no começo é o sinal mais barato de binário.
    """
    sample = content[:2048]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _csv(content: bytes, delimiter: str) -> dict:
    """Planilha vira linhas rotuladas, não uma parede de vírgulas.

    `a,b,c` numa linha só faz o modelo perder a coluna a que cada valor pertence
    depois da terceira linha. Repetir o cabeçalho por valor custa token e paga.
    """
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return _result("extracted", "", None, 0)

    header = rows[0]
    lines = [f"Colunas: {' | '.join(header)}", f"Linhas: {len(rows) - 1}", ""]
    for index, row in enumerate(rows[1:], start=1):
        pairs = [f"{header[i] if i < len(header) else f'col{i}'}={value}" for i, value in enumerate(row) if value]
        lines.append(f"{index}. " + "; ".join(pairs))
        if sum(len(line) for line in lines) > MAX_CHARS:
            lines.append(f"[... {len(rows) - 1 - index} linha(s) restante(s) não incluída(s)]")
            break
    return _truncate("\n".join(lines))


def _json(content: bytes) -> dict:
    parsed = json.loads(content.decode("utf-8", errors="replace"))
    return _truncate(json.dumps(parsed, ensure_ascii=False, indent=2))


def _pdf(content: bytes) -> dict:
    """PDF com camada de texto. Escaneado não tem — e a mensagem diz isso.

    `pypdf` é puro Python e sem dependência transitiva pesada; OCR (que
    resolveria o escaneado) traria Tesseract junto, e não vale antes de alguém
    precisar de verdade.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return _result(
            "unsupported", None,
            "Leitura de PDF indisponível neste ambiente (pypdf não instalado).",
        )

    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"--- Página {number} ---\n{text}")
        if sum(len(item) for item in pages) > MAX_CHARS:
            break

    if not pages:
        return _result(
            "unsupported", None,
            f"PDF sem camada de texto ({len(reader.pages)} página(s)) — provavelmente escaneado. "
            "Precisaria de OCR, que não está configurado.",
        )
    return _truncate("\n\n".join(pages))
