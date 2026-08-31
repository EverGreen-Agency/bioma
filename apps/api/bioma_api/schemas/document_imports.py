from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentImportCandidate(BaseModel):
    id: str
    kind: Literal["story", "milestone", "opportunity_event"]
    title: str
    summary: str | None = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    backlog_status: Literal["candidate"] = "candidate"
    acceptance_criteria: str | None = None
    definition_of_done: str | None = None
    planned_start_at: date | None = None
    planned_end_at: date | None = None
    source_excerpt: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectDocumentImport(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    source_name: str
    content_type: str
    content_hash: str
    source_size_bytes: int
    extracted_title: str | None = None
    extracted_text: str
    extraction_version: str
    status: Literal["draft", "materialized", "rejected"]
    candidates: list[DocumentImportCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    materialized_item_ids: list[UUID] = Field(default_factory=list)
    created_by: UUID | None = None
    materialized_by: UUID | None = None
    materialized_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProjectDocumentImportMaterialize(BaseModel):
    confirm: Literal[True]
    candidate_ids: list[str] = Field(min_length=1, max_length=200)
    create_tasks: bool = False
