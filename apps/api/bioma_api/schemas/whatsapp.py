from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

WhatsAppProviderType = Literal["evolution", "meta_cloud", "zapi", "custom"]
WhatsAppMessageType = Literal["text", "template", "media"]


class WhatsAppProviderConfigPayload(BaseModel):
    provider_type: WhatsAppProviderType
    api_url: str | None = Field(default=None, max_length=1000)
    api_token: str | None = Field(default=None, max_length=1000)
    instance_name: str | None = Field(default=None, max_length=300)
    phone_number: str | None = Field(default=None, max_length=50)
    status: Literal["active", "inactive", "error"] = Field(default="active")
    metadata: dict = Field(default_factory=dict)


class WhatsAppProviderConfigSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    provider_type: WhatsAppProviderType
    api_url: str | None = None
    instance_name: str | None = None
    phone_number: str | None = None
    status: Literal["active", "inactive", "error"]
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WhatsAppSendMessagePayload(BaseModel):
    provider_type: WhatsAppProviderType
    to_number: str = Field(min_length=8, max_length=30)
    message_text: str = Field(min_length=1, max_length=4000)
    template_name: str | None = Field(default=None, max_length=300)
    template_variables: list[str] = Field(default_factory=list)


class WhatsAppMessageLogSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    provider_type: WhatsAppProviderType
    to_number: str
    message_type: WhatsAppMessageType
    payload: dict
    status: Literal["queued", "sent", "delivered", "read", "failed"]
    error_message: str | None = None
    sent_at: datetime
