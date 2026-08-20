from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

CmsKind = Literal["wordpress"]
PublishMode = Literal["draft", "direct"]


class CmsTarget(BaseModel):
    id: UUID
    workspace_id: UUID
    label: str
    kind: CmsKind
    site_url: str
    credential_id: UUID
    credential_label: str
    publish_mode: PublishMode
    is_active: bool
    last_checked_at: datetime | None = None
    # Guardado inclusive quando falhou: mostrar só o sucesso deixaria a tela
    # dizendo "verificado" para um alvo que parou de funcionar depois.
    last_check_error: str | None = None
    created_at: datetime
    updated_at: datetime


class CmsTargetCreate(BaseModel):
    label: str = Field(min_length=2, max_length=120)
    kind: CmsKind = "wordpress"
    site_url: str = Field(min_length=8, max_length=2000)
    credential_id: UUID
    publish_mode: PublishMode = "draft"

    @field_validator("site_url")
    @classmethod
    def exigir_https(cls, value: str) -> str:
        limpo = value.strip().rstrip("/")
        if not limpo.startswith("https://"):
            raise ValueError(
                "O endereço precisa usar HTTPS. Application Password viaja em "
                "Basic Auth: sem TLS a senha vai em texto claro."
            )
        return limpo


class CmsTargetUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=120)
    credential_id: UUID | None = None
    publish_mode: PublishMode | None = None
    is_active: bool | None = None


class CmsTargetCheck(BaseModel):
    """Resultado do teste de conexão. `ok=False` vem com o motivo, não com um
    código."""

    ok: bool
    detail: str


class PublicationPreview(BaseModel):
    """Exatamente o que seria enviado — sem enviar.

    Existe porque o destino é o site do CLIENTE. Ver antes não é conforto: é o
    que separa um erro corrigível de um post publicado em nome dele.
    """

    target_id: UUID
    artifact_id: UUID
    version: int
    # `draft` ou `publish`, já resolvido pelas regras da decisão 14 (modo do
    # alvo + status da peça). É o que de fato aconteceria.
    resulting_status: str
    # Motivo quando o resultado não é o que o modo do alvo sugeria — por
    # exemplo, alvo em "direto" com peça não aprovada.
    downgrade_reason: str | None = None
    payload: dict[str, Any]


class ArtifactPublication(BaseModel):
    id: UUID
    artifact_id: UUID
    version: int
    target_id: UUID
    target_label: str
    site_url: str
    external_id: str
    external_url: str | None = None
    # Status COMO O CMS DEVOLVEU, não como pedimos: o WordPress pode rebaixar
    # conforme o papel do usuário, e registrar a intenção faria a tela mentir.
    external_status: str | None = None
    published_at: datetime


class PublishRequest(BaseModel):
    target_id: UUID
    # Nulo publica a versão corrente. Explícito republica uma antiga — que é o
    # caso de "voltar para a v2", e sem isso a única saída seria criar uma v4
    # copiando a v2.
    version: int | None = None
    slug: str | None = Field(default=None, max_length=200)
    categories: list[int] | None = None
    tags: list[int] | None = None
