from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ClientFileVisibility = Literal["internal", "client"]


class ClientFileSummary(BaseModel):
    id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    visibility: ClientFileVisibility
    uploaded_by: UUID | None = None
    created_at: datetime


class ClientFileDownloadResponse(BaseModel):
    url: str
    expires_in: int
