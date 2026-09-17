"""Regras do Wiki EG: base de conhecimento interna, só platform_admin.

Documentos são markdown no Postgres. Anexos binários vão para o S3 via
storage.py, seguindo o mesmo padrão de files.py (chave única, limite de
tamanho, URL assinada de curta duração, limpeza no S3 antes do banco).
"""

import re
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from bioma_api.access import require_platform_admin
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.repositories import wiki as wiki_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.wiki import (
    WikiAttachmentDownload,
    WikiAttachmentSummary,
    WikiDocumentCreate,
    WikiDocumentDetail,
    WikiDocumentSummary,
    WikiDocumentUpdate,
    WikiImportResult,
)
from bioma_api.services import storage
from bioma_api.services.storage import StorageNotConfiguredError, StorageOperationError


def _tenant_id(conn, user: CurrentUserResponse) -> UUID:
    tenant_id = workspaces_repo.find_platform_tenant_id(conn, user.id)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant administrativo não encontrado para o Wiki EG.",
        )
    return tenant_id


def _safe_filename(file_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", file_name).strip("-")
    return normalized or "arquivo"


def _knowledge_dir() -> Path | None:
    """Diretório dos manuais core (`seed_data/knowledge` ou fallback no monorepo)."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "seed_data" / "knowledge"
        if candidate.is_dir():
            return candidate
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "_opensquad" / "_memory" / "knowledge"
        if candidate.is_dir():
            return candidate
    return None


def _clean_title(filename: str) -> str:
    stem = Path(filename).stem
    if "__" in stem:
        _, _, stem = stem.partition("__")
    clean = stem.replace("_", " ").strip()
    return re.sub(r"\s+", " ", clean)


def _categorize(name: str) -> str:
    lower = name.lower()
    if any(token in lower for token in ("comercial", "raio-x", "vendas")):
        return "comercial"
    if any(token in lower for token in ("_rh_", " rh ", "pessoas", "recrutamento")):
        return "rh"
    if "mestre" in lower:
        return "geral"
    return "operacao"


def import_core_documents(user: CurrentUserResponse) -> WikiImportResult:
    """Importa os manuais markdown de `seed_data/knowledge` para o Wiki.

    Idempotente por título. Limpa prefixos brutos (ex: knowledge__), ignora
    READMEs e limpa títulos antigos salvos no banco.
    """
    require_platform_admin(user)
    directory = _knowledge_dir()
    if directory is None:
        return WikiImportResult(imported=[], skipped=[], available=False)

    imported: list[str] = []
    skipped: list[str] = []
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        # Limpa eventuais READMEs legados no banco
        conn.execute("delete from wiki_documents where tenant_organization_id = %s and lower(title) like '%%readme%%'", (tenant_id,))

        for path in sorted(directory.glob("*.md")) + sorted(directory.glob("*.markdown")):
            if "readme" in path.name.lower():
                continue

            raw_title = path.stem
            clean_title = _clean_title(path.name)

            # Sanitiza título de documentos já importados com nome bruto (ex: `knowledge__...`)
            conn.execute(
                """
                update wiki_documents
                set title = %s
                where tenant_organization_id = %s and lower(title) = lower(%s)
                """,
                (clean_title, tenant_id, raw_title),
            )

            if wiki_repo.title_exists(conn, tenant_id, clean_title) or wiki_repo.title_exists(conn, tenant_id, raw_title):
                skipped.append(clean_title)
                continue

            content = path.read_text(encoding="utf-8", errors="replace")
            wiki_repo.create_document(conn, tenant_id, user.id, _categorize(path.name), clean_title, content)
            imported.append(clean_title)

    return WikiImportResult(imported=imported, skipped=skipped, available=True)


def auto_sanitize_and_seed(conn, tenant_id: UUID, user_id: UUID) -> None:
    # 1. Limpa títulos no banco que possuam prefixos 'knowledge__', 'company__', 'architecture__' ou underlines brutos
    conn.execute(
        """
        update wiki_documents
        set title = trim(regexp_replace(
            regexp_replace(title, '^(knowledge__|company__|architecture__)', '', 'i'),
            '_', ' ', 'g'
        ))
        where tenant_organization_id = %s
          and (
            lower(title) like 'knowledge__%%' 
            or lower(title) like 'company__%%' 
            or lower(title) like 'architecture__%%'
            or title like '%%_%%'
          )
        """,
        (tenant_id,),
    )
    # 2. Deleta READMEs legados no banco
    conn.execute(
        "delete from wiki_documents where tenant_organization_id = %s and lower(title) like '%%readme%%'",
        (tenant_id,),
    )
    # 3. Se a Wiki estiver vazia para este tenant, efetua a carga automática do seed_data
    count = conn.execute(
        "select count(*) as total from wiki_documents where tenant_organization_id = %s",
        (tenant_id,),
    ).fetchone()["total"]
    if count == 0:
        directory = _knowledge_dir()
        if directory and directory.is_dir():
            for path in sorted(directory.glob("*.md")) + sorted(directory.glob("*.markdown")):
                if "readme" in path.name.lower():
                    continue
                clean_title = _clean_title(path.name)
                content = path.read_text(encoding="utf-8", errors="replace")
                wiki_repo.create_document(conn, tenant_id, user_id, _categorize(path.name), clean_title, content)


def list_documents(user: CurrentUserResponse) -> list[WikiDocumentSummary]:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        auto_sanitize_and_seed(conn, tenant_id, user.id)
        rows = wiki_repo.list_documents(conn, tenant_id)
    return [WikiDocumentSummary(**row) for row in rows]


def get_document(document_id: UUID, user: CurrentUserResponse) -> WikiDocumentDetail:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        doc = wiki_repo.get_document(conn, tenant_id, document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
        attachments = wiki_repo.list_attachments(conn, document_id)
    return WikiDocumentDetail(
        **doc,
        attachments=[WikiAttachmentSummary(**attachment) for attachment in attachments],
    )


def create_document(payload: WikiDocumentCreate, user: CurrentUserResponse) -> WikiDocumentDetail:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        document_id = wiki_repo.create_document(
            conn, tenant_id, user.id, payload.category, payload.title.strip(), payload.content
        )
    return get_document(document_id, user)


def update_document(document_id: UUID, payload: WikiDocumentUpdate, user: CurrentUserResponse) -> WikiDocumentDetail:
    require_platform_admin(user)
    fields = payload.model_dump(exclude_unset=True)
    if "title" in fields and fields["title"] is not None:
        fields["title"] = fields["title"].strip()
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        if not wiki_repo.update_document(conn, tenant_id, document_id, fields):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
    return get_document(document_id, user)


def delete_document(document_id: UUID, user: CurrentUserResponse) -> None:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        if not wiki_repo.document_exists(conn, tenant_id, document_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
        keys = wiki_repo.delete_document(conn, tenant_id, document_id)
    # Limpa o S3 depois de o banco confirmar; falha de storage não trava a exclusão.
    for key in keys:
        try:
            storage.delete_object(key)
        except (StorageNotConfiguredError, StorageOperationError):
            pass


async def add_attachment(document_id: UUID, upload: UploadFile, user: CurrentUserResponse) -> WikiAttachmentSummary:
    require_platform_admin(user)
    settings = get_settings()
    content = await upload.read()
    max_bytes = settings.storage_max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo maior que o limite de {settings.storage_max_upload_mb} MB.",
        )
    file_name = _safe_filename(upload.filename or "arquivo")
    content_type = upload.content_type or "application/octet-stream"

    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        if not wiki_repo.document_exists(conn, tenant_id, document_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
        storage_key = f"wiki/{tenant_id}/{document_id}/{uuid4()}-{file_name}"
        try:
            storage.put_object(storage_key, content, content_type)
        except StorageNotConfiguredError:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Armazenamento de anexos não configurado neste ambiente.")
        except StorageOperationError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
        row = wiki_repo.add_attachment(conn, document_id, user.id, file_name, storage_key, content_type, len(content))
    return WikiAttachmentSummary(**row)


def download_attachment(attachment_id: UUID, user: CurrentUserResponse) -> WikiAttachmentDownload:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        row = wiki_repo.get_attachment(conn, tenant_id, attachment_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")
    try:
        url = storage.presigned_get_url(row["storage_key"], expires_in=300)
    except StorageNotConfiguredError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Armazenamento de anexos não configurado neste ambiente.")
    except StorageOperationError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    return WikiAttachmentDownload(url=url, file_name=row["file_name"])


def delete_attachment(attachment_id: UUID, user: CurrentUserResponse) -> None:
    require_platform_admin(user)
    with connect() as conn:
        tenant_id = _tenant_id(conn, user)
        key = wiki_repo.delete_attachment(conn, tenant_id, attachment_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")
    try:
        storage.delete_object(key)
    except (StorageNotConfiguredError, StorageOperationError):
        pass
