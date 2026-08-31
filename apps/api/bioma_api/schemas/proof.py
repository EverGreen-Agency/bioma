from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProofUptime(BaseModel):
    monitor_id: str
    monitor_name: str
    kind: str
    window_days: int
    availability: float
    number_of_incidents: int
    total_downtime_seconds: int
    # Desde quando existe medição. É o que impede "100% em 90 dias" num monitor
    # de um dia parecer resultado em vez de falta de histórico.
    measured_since: date | None = None
    collected_at: datetime


class ProofDailyPoint(BaseModel):
    date: date
    availability: float


class ProofDelivery(BaseModel):
    id: UUID
    title: str
    completed_at: datetime
    workspace_name: str | None = None


class ProofFix(BaseModel):
    id: UUID
    title: str
    resolved_at: datetime
    minutes_to_resolve: int


class ProofPanel(BaseModel):
    generated_at: date
    # Vazio = ninguém mediu ainda. A tela precisa distinguir isso de 100%.
    uptime: list[ProofUptime] = Field(default_factory=list)
    daily_uptime: list[ProofDailyPoint] = Field(default_factory=list)
    deliveries: list[ProofDelivery] = Field(default_factory=list)
    open_issues: int = 0
    fixes: list[ProofFix] = Field(default_factory=list)
