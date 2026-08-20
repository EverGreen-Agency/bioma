from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ArtifactStatus = Literal["draft", "approved", "published", "archived"]
ArtifactVisibility = Literal["internal", "client"]


class StudioArtifactVersion(BaseModel):
    id: UUID
    artifact_id: UUID
    version: int
    title: str
    content: str | None = None
    url: str | None = None
    # Preenchido quando ESTA versão saiu de uma execução do copiloto; nulo
    # quando alguém editou à mão. A diferença entre as duas é o que se quer
    # saber ao revisar.
    run_id: UUID | None = None
    change_note: str | None = None
    created_by: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime


class StudioArtifact(BaseModel):
    id: UUID
    organization_id: UUID
    workspace_id: UUID | None = None
    title: str
    # Aberto de propósito: roteiro, post, legenda, prompt de arte, planejamento.
    # Enum aqui obrigaria migração a cada formato novo.
    kind: str
    visibility: ArtifactVisibility
    status: ArtifactStatus
    url: str | None = None
    content: str | None = None
    current_version: int
    versions_total: int = 1
    # Procedência: de qual conversa e execução a peça saiu.
    thread_id: UUID | None = None
    run_id: UUID | None = None
    created_by: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime


class StudioArtifactDetail(StudioArtifact):
    versions: list[StudioArtifactVersion] = Field(default_factory=list)


class StudioArtifactCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    kind: str = Field(min_length=2, max_length=60)
    content: str | None = None
    url: str | None = Field(default=None, max_length=2000)
    visibility: ArtifactVisibility = "internal"
    status: ArtifactStatus = "draft"
    thread_id: UUID | None = None
    run_id: UUID | None = None
    change_note: str | None = Field(default=None, max_length=500)


class StudioArtifactVersionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    content: str | None = None
    url: str | None = Field(default=None, max_length=2000)
    run_id: UUID | None = None
    change_note: str | None = Field(default=None, max_length=500)


class StudioArtifactFromRun(BaseModel):
    """Salvar a resposta de uma execução do copiloto como artefato.

    `thread_id` e `run_id` NÃO estão aqui de propósito: o servidor os deduz da
    execução. Aceitá-los do cliente permitiria salvar um material apontando
    para uma conversa que não o gerou — procedência que mente é pior que
    procedência ausente.
    """

    title: str = Field(min_length=2, max_length=240)
    kind: str = Field(default="roteiro", min_length=2, max_length=60)
    # Nulo = usa a resposta da execução como está. Preenchido = a pessoa editou
    # antes de salvar, e é o texto dela que vale.
    content: str | None = None
    visibility: ArtifactVisibility = "internal"
    # Preenchido quando a conversa nasceu fora de um workspace (ex.: cockpit).
    workspace_id: UUID | None = None
    # Preenchido para salvar como PRÓXIMA VERSÃO de um artefato existente, em
    # vez de criar outro. É assim que "regerar" deixa de perder o anterior.
    artifact_id: UUID | None = None
    change_note: str | None = Field(default=None, max_length=500)


class StudioArtifactStatusUpdate(BaseModel):
    status: ArtifactStatus


class StudioArtifactKindCount(BaseModel):
    kind: str
    total: int


class ContentQualityCheck(BaseModel):
    id: str
    family: Literal["seo", "geo"]
    label: str
    passed: bool
    # False = nao ha o que avaliar (texto sem imagem, por exemplo). Sai do
    # denominador do score em vez de virar aprovacao de graca.
    applicable: bool
    weight: int
    hint: str


class ContentQualityRequest(BaseModel):
    title: str = Field(default="", max_length=240)
    content: str = Field(default="", max_length=200_000)
    # Opcional de proposito: reprovar por uma palavra-chave que ninguem
    # informou seria punir o texto por uma escolha que nao foi feita.
    keyword: str | None = Field(default=None, max_length=120)


class ContentQualityReport(BaseModel):
    """Prontidao para publicar. NAO e previsao de posicao no Google.

    Todo sinal aqui sai do proprio texto; autoridade de dominio, backlinks e
    concorrencia do termo nao entram na conta e nao ha como estimar ranking
    sem eles."""

    score: int
    seo_score: int
    geo_score: int
    words: int
    checks: list[ContentQualityCheck]
