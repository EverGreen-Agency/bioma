from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GitHubConnectionInput(BaseModel):
    repository: str = Field(min_length=3, max_length=240, examples=["evergreen-ai-os/bioma"])
    default_branch: str = Field(default="main", min_length=1, max_length=240)
    status: Literal["active", "paused"] = "active"

    @field_validator("repository")
    @classmethod
    def valid_repository(cls, value: str) -> str:
        normalized = value.strip().removeprefix("https://github.com/").removesuffix(".git").strip("/")
        parts = normalized.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("Informe o repositório no formato owner/repository.")
        return normalized


class GitHubConnectionSummary(BaseModel):
    id: UUID
    project_id: UUID
    repository: str
    default_branch: str
    status: Literal["active", "paused"]
    updated_at: datetime


class GitHubIssueSummary(BaseModel):
    number: int
    title: str
    state: str
    url: str
    labels: list[str]
    updated_at: datetime


class GitHubPullRequestSummary(BaseModel):
    number: int
    title: str
    state: str
    draft: bool
    url: str
    source_branch: str
    target_branch: str
    updated_at: datetime


class GitHubCommitSummary(BaseModel):
    sha: str
    message: str
    url: str
    author_name: str | None = None
    authored_at: datetime | None = None


class GitHubProjectActivity(BaseModel):
    project_id: UUID
    repository: str
    default_branch: str
    fetched_at: datetime
    issues: list[GitHubIssueSummary]
    pull_requests: list[GitHubPullRequestSummary]
    commits: list[GitHubCommitSummary]


class GitHubIssueCreateRequest(BaseModel):
    body: str | None = None
    confirm: bool = Field(
        description="Confirmação explícita e obrigatória: cria uma issue real e pública no repositório GitHub.",
    )

    @field_validator("confirm")
    @classmethod
    def must_confirm(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Confirmação explícita obrigatória (confirm=true) para escrever no GitHub.")
        return value


class GitHubIssueLinkSummary(BaseModel):
    deliverable_id: UUID
    repository: str
    issue_number: int
    issue_url: str


class GitHubActivitySyncRequest(BaseModel):
    confirm: bool
    idempotency_key: str = Field(min_length=8, max_length=255)
    client_visible: bool = True
    summary_override: str | None = Field(default=None, min_length=3, max_length=1_000)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("confirm")
    @classmethod
    def must_confirm_sync(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Confirmação HITL obrigatória para publicar a atualização no projeto.")
        return value


class GitHubActivitySyncResult(BaseModel):
    project_id: UUID
    project_update_id: UUID
    idempotency_key: str
    repository: str
    client_visible: bool
    created_at: datetime


class GitHubCompletionSuggestion(BaseModel):
    """Divergência observada: a issue fechou lá, a entrega segue aberta aqui."""
    deliverable_id: UUID
    deliverable_title: str
    deliverable_status: str
    issue_number: int
    issue_url: str | None
    issue_title: str


class GitHubCompletionSuggestions(BaseModel):
    project_id: UUID
    repository: str
    # Momento da leitura no GitHub. É sugestão calculada na hora, não estado
    # guardado — sem isto não dá para saber se o dado é de agora ou de ontem.
    checked_at: datetime
    suggestions: list[GitHubCompletionSuggestion] = Field(default_factory=list)
