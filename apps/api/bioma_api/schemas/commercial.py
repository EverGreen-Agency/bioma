from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


PilarType = Literal["oferta", "demanda", "conversao"]
MaturityLevel = Literal["semente", "muda", "arvore", "floresta"]
PlanStatus = Literal["em_andamento", "concluido", "pausado"]


class CommercialScoreSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    oferta_score: float
    demanda_score: float
    conversao_score: float
    oferta_level: int
    demanda_level: int
    conversao_level: int
    gargalo_prioritario: PilarType
    maturity_level: MaturityLevel
    updated_at: datetime
    created_at: datetime


class DiagnosticAnswerRequest(BaseModel):
    pilar: PilarType
    regua_level: Literal[1, 2]
    question_key: str = Field(..., min_length=1)
    score_value: float = Field(..., ge=0.0, le=10.0)
    notes: Optional[str] = None


class DiagnosticAnswerSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    pilar: PilarType
    regua_level: int
    question_key: str
    score_value: float
    notes: Optional[str] = None
    updated_at: datetime


class ActionPlanCreateRequest(BaseModel):
    pilar_gargalo: PilarType
    sprint_title: str = Field(..., min_length=1)
    sprint_goals: str = Field(..., min_length=1)


class ActionPlanStatusUpdateRequest(BaseModel):
    status: PlanStatus


class ActionPlanSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    pilar_gargalo: PilarType
    sprint_title: str
    sprint_goals: str
    status: PlanStatus
    start_date: date
    end_date: Optional[date] = None
    created_at: datetime


class CommercialPortalResponse(BaseModel):
    scores: CommercialScoreSummary
    answers: list[DiagnosticAnswerSummary]
    action_plans: list[ActionPlanSummary]
