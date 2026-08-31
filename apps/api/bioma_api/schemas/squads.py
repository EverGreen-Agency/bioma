from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

PilarType = Literal["oferta", "demanda", "conversao", "onboarding", "planning"]


class SquadDefinitionPayload(BaseModel):
    pilar: PilarType
    squad_slug: str = Field(min_length=2, max_length=100)
    squad_name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    agents_config: list[dict] = Field(default_factory=list)
    pipeline_yaml: str | None = Field(default=None, max_length=10000)
    status: Literal["active", "paused"] = Field(default="active")


class SquadDefinitionSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    pilar: PilarType
    squad_slug: str
    squad_name: str
    description: str | None = None
    agents_config: list[dict] = Field(default_factory=list)
    pipeline_yaml: str | None = None
    status: Literal["active", "paused"]
    created_at: datetime
    updated_at: datetime


class RunSquadPayload(BaseModel):
    pilar: PilarType
    squad_slug: str = Field(min_length=2, max_length=100)
    squad_name: str = Field(min_length=2, max_length=200)
    input_data: dict = Field(default_factory=dict)


class SquadExecutionSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    squad_id: UUID | None = None
    pilar: PilarType
    squad_name: str
    triggered_by: str
    status: Literal["running", "completed", "failed"]
    generation_mode: Literal["live", "preview", "manual"]
    input_data: dict
    output_data: dict
    token_usage: dict
    estimated_cost_cents: int
    execution_logs: list[dict]
    started_at: datetime
    completed_at: datetime | None = None


class FinOpsSummaryResponse(BaseModel):
    workspace_id: UUID
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_cost_cents: int
    total_executions: int
