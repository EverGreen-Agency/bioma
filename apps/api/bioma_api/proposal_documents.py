from __future__ import annotations

import re
import textwrap
from typing import Any


def render_proposal_markdown(proposal: dict[str, Any]) -> str:
    title = proposal.get("title") or f"Proposta para {proposal.get('client_name', 'cliente')}"
    contractor = proposal.get("contractor_name") or "Evergreen Growth"
    services = proposal.get("scope_items") or []
    scope_lines = "\n".join(
        f"- {item.get('item', 'Entrega')}: {item.get('description') or item.get('pilar') or 'escopo a validar'}"
        for item in services
    ) or "- Escopo a validar com o cliente."
    team = ", ".join(proposal.get("team_members") or []) or "Equipe definida após aprovação."
    return f"""# {title}

**{contractor} apresenta esta proposta para {proposal.get('client_name', 'o cliente')}.**

## Contexto e objetivo

{proposal.get('problem_summary') or proposal.get('executive_summary') or 'Contexto a validar.'}

## Abordagem recomendada

{proposal.get('executive_summary') or 'Abordagem a validar.'}

## Escopo e entregas

{scope_lines}

## Modelo de execução

- Modalidade: {proposal.get('delivery_modality') or 'A definir'}
- Equipe: {team}
- Prazo estimado: {proposal.get('delivery_days') or 'A definir'} dias

## Investimento e condições

- Investimento: {proposal.get('estimated_budget') or _format_cents(proposal.get('pricing_cents', 0))}
- Pagamento: {proposal.get('payment_terms') or 'Condições a validar'}
- Urgência: {proposal.get('urgency') or 'A definir'}

## Premissas e validação

{proposal.get('special_requirements') or 'A execução depende da validação do escopo, dos acessos e das responsabilidades das partes.'}

## Próximo passo

Revisar o escopo, registrar os ajustes necessários e formalizar o aceite.
"""


def render_proposal_pdf(proposal: dict[str, Any]) -> bytes:
    """Generate a dependency-free, printable PDF for the reviewed proposal."""
    markdown = proposal.get("content_markdown") or render_proposal_markdown(proposal)
    plain_lines = _markdown_to_lines(markdown)
    wrapped: list[str] = []
    for line in plain_lines:
        if not line:
            wrapped.append("")
            continue
        wrapped.extend(textwrap.wrap(line, width=92, break_long_words=False) or [""])

    page_size = 47
    pages = [wrapped[index:index + page_size] for index in range(0, len(wrapped), page_size)] or [[]]
    objects: list[bytes] = []

    def add_object(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    bold_font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    page_ids: list[int] = []
    content_ids: list[int] = []
    pages_id_placeholder = 0

    for page_number, page_lines in enumerate(pages, start=1):
        commands = [
            "BT",
            f"/F{bold_font_id} 15 Tf",
            "50 795 Td",
            f"({_pdf_escape(proposal.get('title') or 'Proposta comercial')}) Tj",
            "0 -25 Td",
            f"/F{font_id} 9 Tf",
        ]
        for line in page_lines:
            commands.append(f"({_pdf_escape(line)}) Tj")
            commands.append("0 -14 Td")
        commands.extend([
            "ET",
            "BT",
            f"/F{font_id} 8 Tf",
            "50 28 Td",
            f"(Evergreen Growth - pagina {page_number} de {len(pages)}) Tj",
            "ET",
        ])
        stream = "\n".join(commands).encode("cp1252", errors="replace")
        content_ids.append(add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        ))
        page_ids.append(add_object(b""))

    pages_id = add_object(
        f"<< /Type /Pages /Count {len(page_ids)} /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] >>".encode()
    )
    pages_id_placeholder = pages_id
    for page_id, content_id in zip(page_ids, content_ids, strict=True):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_id_placeholder} 0 R "
            f"/MediaBox [0 0 595 842] /Resources << /Font << "
            f"/F{font_id} {font_id} 0 R /F{bold_font_id} {bold_font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode()
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)


def _markdown_to_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "• ", line)
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        lines.append(line)
    return lines


def _pdf_escape(value: Any) -> str:
    text = str(value or "").encode("cp1252", errors="replace").decode("cp1252")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_cents(value: int | None) -> str:
    if not value:
        return "A definir"
    return f"R$ {value / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
