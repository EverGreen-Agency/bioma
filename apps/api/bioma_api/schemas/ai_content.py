from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ContentChannel = Literal["instagram", "linkedin", "facebook", "tiktok", "youtube"]
ContentType = Literal["social_posts", "image_generation", "video_scripts"]
ImageProvider = Literal["dalle_3", "flux", "higgsfield", "midjourney_api", "custom"]


class AiContentRequestCreate(BaseModel):
    content_type: ContentType = Field(default="social_posts")
    brief: str = Field(min_length=10, max_length=6000)
    channels: list[ContentChannel] = Field(min_length=1)
    quantity: int = Field(default=3, ge=1, le=12)
    tone: str | None = Field(default=None, max_length=300)
    objective: str | None = Field(default=None, max_length=500)
    methodology_refs: list[str] = Field(default_factory=list, max_length=20)
    image_provider: ImageProvider | None = Field(default="dalle_3")


class AiContentPost(BaseModel):
    title: str
    channel: ContentChannel
    format: str
    hook: str
    caption: str
    cta: str


class AiContentImage(BaseModel):
    title: str
    channel: ContentChannel
    aspect_ratio: str  # "1:1", "9:16", "16:9"
    visual_description: str
    prompt_en: str
    provider: str
    preview_url: str | None = None


class AiContentVideoScript(BaseModel):
    title: str
    channel: ContentChannel
    format: str  # "reels", "tiktok", "youtube_shorts", "video_ad"
    duration_seconds: int
    hook_0_3s: str
    script_body: str
    cta_final: str
    broll_notes: str
    camera_angle_notes: str | None = None


class AiContentOutput(BaseModel):
    strategy_note: str
    posts: list[AiContentPost] = Field(default_factory=list)
    images: list[AiContentImage] = Field(default_factory=list)
    video_scripts: list[AiContentVideoScript] = Field(default_factory=list)


class AiContentRequestSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    content_type: ContentType
    status: Literal["queued", "running", "ready", "error", "cancelled"]
    brief: str
    channels: list[ContentChannel]
    quantity: int
    tone: str | None = None
    objective: str | None = None
    methodology_refs: list[str]
    provider: str | None = None
    model: str | None = None
    generation_mode: Literal["live", "preview"] | None = None
    output: AiContentOutput | None = None
    error_message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
