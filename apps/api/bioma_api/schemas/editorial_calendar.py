from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

ContentType = Literal["social_post", "image_ad", "video_script", "article"]
ChannelType = Literal["instagram", "facebook", "linkedin", "youtube", "tiktok", "blog"]
StageType = Literal["ideation", "production", "review", "approved", "scheduled", "published"]


class EditorialCalendarItemPayload(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content_type: ContentType = Field(default="social_post")
    channel: ChannelType = Field(default="instagram")
    scheduled_at: datetime | None = None
    stage: StageType = Field(default="ideation")
    post_text: str | None = Field(default=None, max_length=5000)
    media_urls: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class EditorialCalendarItemSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    content_type: ContentType
    channel: ChannelType
    scheduled_at: datetime | None = None
    stage: StageType
    post_text: str | None = None
    media_urls: list[str]
    metadata: dict
    created_at: datetime
    updated_at: datetime
