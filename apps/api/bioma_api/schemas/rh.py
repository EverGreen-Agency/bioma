from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MilestoneTemplateStatus = Literal["active", "archived"]
MilestoneStatus = Literal["pending", "done"]


class MilestoneTemplateCreateRequest(BaseModel):
    day_offset: int = Field(ge=0)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: MilestoneTemplateStatus = "active"


class MilestoneTemplateUpdateRequest(BaseModel):
    day_offset: int | None = Field(default=None, ge=0)
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: MilestoneTemplateStatus | None = None


class MilestoneTemplateSummary(BaseModel):
    id: UUID
    day_offset: int
    title: str
    description: str | None = None
    status: MilestoneTemplateStatus
    created_at: datetime
    updated_at: datetime


class OnboardingMilestoneEntry(BaseModel):
    template_id: UUID | None = None
    day_offset: int
    title: str
    status: MilestoneStatus = "pending"
    completed_at: datetime | None = None


class OnboardingPlanCreateRequest(BaseModel):
    user_id: UUID
    hire_date: date


class OnboardingPlanSummary(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str
    user_name: str
    hire_date: date
    milestones: list[OnboardingMilestoneEntry] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MilestoneCompletionRequest(BaseModel):
    day_offset: int
    status: MilestoneStatus


class SatisfactionScoreCreateRequest(BaseModel):
    score: float = Field(ge=0, le=10)
    source: str = Field(default="manual", max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class SatisfactionScoreSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    score: float
    source: str
    notes: str | None = None
    captured_at: datetime


class ManagerPortfolioWorkspace(BaseModel):
    workspace_id: UUID
    workspace_name: str
    client_name: str
    projects_total: int
    deliverables_total: int
    deliverables_done: int
    deliverables_overdue: int
    deliverables_blocked: int
    completion_percentage: float
    pace_status: Literal["unknown", "on_track", "at_risk", "off_track"]
    latest_satisfaction_score: float | None = None
    latest_satisfaction_captured_at: datetime | None = None


class ManagerPortfolioResponse(BaseModel):
    user_id: UUID
    user_name: str
    workspaces: list[ManagerPortfolioWorkspace] = Field(default_factory=list)
