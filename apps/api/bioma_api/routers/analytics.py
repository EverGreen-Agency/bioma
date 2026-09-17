from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.services import kommo as kommo_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


class PipelineMetrics(BaseModel):
    pipeline_id: str
    pipeline_name: str
    snapshot_date: str
    total_leads: int
    won_leads: int
    lost_leads: int
    active_leads: int
    total_value: float
    won_value: float


class KommoMetricsResponse(BaseModel):
    pipelines: list[PipelineMetrics]


@router.get("/{organization_id}/kommo", response_model=KommoMetricsResponse)
def get_kommo_analytics(
    organization_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> KommoMetricsResponse:
    rows = kommo_service.get_metrics(user, organization_id)
    return KommoMetricsResponse(
        pipelines=[
            PipelineMetrics(
                pipeline_id=row["pipeline_id"],
                pipeline_name=row["pipeline_name"],
                snapshot_date=str(row["snapshot_date"]),
                total_leads=row["total_leads"],
                won_leads=row["won_leads"],
                lost_leads=row["lost_leads"],
                active_leads=row["active_leads"],
                total_value=float(row["total_value"]),
                won_value=float(row["won_value"]),
            )
            for row in rows
        ]
    )
