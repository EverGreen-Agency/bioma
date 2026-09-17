from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

WikiCategory = Literal["comercial", "rh", "operacao", "geral"]


class WikiAttachmentSummary(BaseModel):
    id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class WikiDocumentSummary(BaseModel):
    id: UUID
    category: WikiCategory
    title: str
    updated_at: datetime
    attachment_count: int


class WikiDocumentDetail(BaseModel):
    id: UUID
    category: WikiCategory
    title: str
    content: str
    updated_at: datetime
    attachments: list[WikiAttachmentSummary]


class WikiDocumentCreate(BaseModel):
    category: WikiCategory = "geral"
    title: str = Field(min_length=1, max_length=200)
    content: str = ""


class WikiDocumentUpdate(BaseModel):
    category: WikiCategory | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None


class WikiAttachmentDownload(BaseModel):
    url: str
    file_name: str


class WikiImportResult(BaseModel):
    imported: list[str]
    skipped: list[str]
    available: bool  # False quando o diretório de manuais não existe (produção)
