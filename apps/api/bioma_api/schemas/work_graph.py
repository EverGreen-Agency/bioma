from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


WorkItemKind = Literal[
    "goal", "spec", "story", "decision", "plan", "milestone", "opportunity_event", "deliverable",
    "test", "evidence", "release", "asset",
]
WorkItemStatus = Literal["draft", "active", "done", "superseded", "archived"]
BacklogStatus = Literal["candidate", "backlog", "ready", "in_progress", "done", "rejected"]
WorkPriority = Literal["low", "medium", "high", "critical"]
WorkEntityType = Literal[
    "workspace", "project", "opportunity", "proposal", "task",
    "document", "document_import", "artifact", "work_item",
]
WorkRelationType = Literal[
    "derives_from", "decomposes_into", "implements", "tests", "evidences",
    "decides", "blocks", "supersedes", "reuses", "materializes",
]


class WorkItemCreate(BaseModel):
    project_id: UUID | None = None
    kind: WorkItemKind
    title: str = Field(min_length=2, max_length=300)
    summary: str | None = Field(default=None, max_length=20_000)
    status: WorkItemStatus = "draft"
    external_ref: str | None = Field(default=None, max_length=2_000)
    backlog_status: BacklogStatus = "candidate"
    priority: WorkPriority = "medium"
    rank: int = Field(default=0, ge=0, le=1_000_000)
    acceptance_criteria: str | None = Field(default=None, max_length=20_000)
    definition_of_done: str | None = Field(default=None, max_length=20_000)
    story_points: int | None = Field(default=None, ge=1, le=100)
    planned_start_at: date | None = None
    planned_end_at: date | None = None
    source_document_import_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=300)
    summary: str | None = Field(default=None, max_length=20_000)
    status: WorkItemStatus | None = None
    external_ref: str | None = Field(default=None, max_length=2_000)
    backlog_status: BacklogStatus | None = None
    priority: WorkPriority | None = None
    rank: int | None = Field(default=None, ge=0, le=1_000_000)
    acceptance_criteria: str | None = Field(default=None, max_length=20_000)
    definition_of_done: str | None = Field(default=None, max_length=20_000)
    story_points: int | None = Field(default=None, ge=1, le=100)
    planned_start_at: date | None = None
    planned_end_at: date | None = None
    metadata: dict[str, Any] | None = None


class WorkItem(WorkItemCreate):
    id: UUID
    workspace_id: UUID
    materialized_task_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkEntityRef(BaseModel):
    type: WorkEntityType
    id: UUID


class WorkLinkCreate(BaseModel):
    source: WorkEntityRef
    relation: WorkRelationType
    target: WorkEntityRef
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkLink(BaseModel):
    id: UUID
    workspace_id: UUID
    source_type: WorkEntityType
    source_id: UUID
    relation_type: WorkRelationType
    target_type: WorkEntityType
    target_id: UUID
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: UUID | None = None
    created_at: datetime


class WorkGraphProjection(BaseModel):
    items: list[WorkItem] = Field(default_factory=list)
    links: list[WorkLink] = Field(default_factory=list)


class WorkItemMaterializeRequest(BaseModel):
    confirm: Literal[True]
