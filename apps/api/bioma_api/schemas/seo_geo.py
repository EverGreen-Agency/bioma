from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AuditCheckItem(BaseModel):
    id: str
    category: str
    label: str
    status: Literal["passed", "warning", "failed"]
    detail: str
    recommendation: str


class TechnicalAudit(BaseModel):
    title: str | None = None
    title_length: int = 0
    description: str | None = None
    description_length: int = 0
    canonical: str | None = None
    h1_tags: list[str] = []
    h2_tags: list[str] = []
    images_total: int = 0
    images_missing_alt: int = 0
    open_graph: dict[str, str] = {}
    checks: list[AuditCheckItem] = []


class GeoAudit(BaseModel):
    llms_txt_present: bool = False
    llms_txt_url: str | None = None
    schemas_detected: list[str] = []
    raw_jsonld_schemas: list[dict[str, Any]] = []
    eeat_signals: dict[str, bool] = {}
    faq_count: int = 0
    ai_search_readiness: Literal["high", "moderate", "low"] = "low"
    checks: list[AuditCheckItem] = []


class SeoGeoAuditRequest(BaseModel):
    url: str = Field(min_length=4, max_length=1000, description="URL do site a ser auditado")


class SeoGeoAuditResponse(BaseModel):
    id: UUID | None = None
    workspace_id: UUID | None = None
    target_url: str
    page_title: str | None = None
    seo_score: float
    geo_score: float
    waf_detected: bool = False
    technical_audit: TechnicalAudit
    geo_audit: GeoAudit
    generated_llms_txt: str = ""
    generated_schema_jsonld: dict[str, Any] = {}
    created_at: datetime | None = None


class SeoGeoAuditSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    target_url: str
    page_title: str | None = None
    seo_score: float
    geo_score: float
    waf_detected: bool = False
    created_at: datetime
