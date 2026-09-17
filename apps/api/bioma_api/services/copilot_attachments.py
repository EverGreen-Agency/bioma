"""Anexos do copiloto: upload, extração de texto e entrega ao modelo.

Escopo: só EG, como todo o copiloto.

Desenho em uma frase: **o arquivo vira texto sempre que possível**, porque texto
funciona em qualquer provedor — inclusive na CLI que roda na cota da assinatura.
Capacidade especial (visão, transcrição) só entra quando não há texto a extrair.
"""

from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from bioma_api import attachment_text
from bioma_api.access import require_platform_admin
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.repositories import copilot_attachments as repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.copilot import CopilotAttachment
from bioma_api.services import storage
from bioma_api.services.storage import StorageNotConfiguredError, StorageOperationError
from bioma_api.worker_bridge import transcribe_audio_safe


def upload(upload_file: UploadFile, thread_id: UUID | None, user: CurrentUserResponse) -> CopilotAttachment:
    require_platform_admin(user)
    settings = get_settings()

    file_name = (upload_file.filename or "arquivo").strip()
    if not file_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome do arquivo é obrigatório.")

    content = upload_file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Arquivo vazio.")

    max_bytes = settings.storage_max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo maior que o limite de {settings.storage_max_upload_mb} MB.",
        )

    content_type = upload_file.content_type or "application/octet-stream"
    kind = attachment_text.classify(content_type, file_name)
    # Extração antes do upload: se o arquivo é ilegível, quem anexou descobre
    # agora, não depois de perguntar algo sobre ele e receber uma resposta vaga.
    # Áudio não tem texto para extrair localmente — a "extração" é chamar o
    # Whisper de verdade, aqui mesmo, pelo mesmo motivo: descobrir agora.
    extraction = transcribe_attachment_audio(content, content_type, file_name) if kind == "audio" else (
        attachment_text.extract(content, content_type, file_name)
    )

    storage_key = f"copilot/{user.id}/{uuid4()}-{_safe_filename(file_name)}"
    try:
        storage.put_object(storage_key, content, content_type)
    except StorageNotConfiguredError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except StorageOperationError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    with connect() as conn:
        row = repo.create(
            conn,
            {
                "thread_id": thread_id,
                "user_id": user.id,
                "file_name": file_name,
                "content_type": content_type,
                "size_bytes": len(content),
                "storage_key": storage_key,
                "kind": kind,
                "extraction_status": extraction["status"],
                "extraction_error": extraction["error"],
                "extracted_text": extraction["text"],
                "truncated_chars": extraction["truncated_chars"],
            },
        )
    return _summary(row)


def remove(attachment_id: UUID, user: CurrentUserResponse) -> dict[str, str]:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.delete(conn, attachment_id, user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")
    try:
        storage.delete_object(row["storage_key"])
    except (StorageNotConfiguredError, StorageOperationError):
        # A linha já saiu do banco; deixar o objeto órfão no bucket é melhor que
        # falhar a remoção e manter um anexo que o usuário mandou apagar.
        pass
    return {"status": "deleted"}


def download_url(attachment_id: UUID, user: CurrentUserResponse) -> dict[str, str]:
    require_platform_admin(user)
    with connect() as conn:
        row = repo.get(conn, attachment_id)
    if not row or row["user_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")
    try:
        return {"url": storage.presigned_get_url(row["storage_key"])}
    except StorageNotConfiguredError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


def load_for_prompt(conn, attachment_ids: list[UUID], user_id: UUID) -> tuple[list[dict], list[dict]]:
    """Devolve `(para o dossiê, para a trilha)`.

    O dossiê leva o conteúdo; a trilha leva só o índice — nome, tipo e se deu
    para ler. Duplicar o texto do anexo na trilha faria dela uma segunda cópia
    do arquivo, e a trilha existe para dizer o que aconteceu, não para
    rearmazenar o que já está no storage.
    """
    rows = repo.list_by_ids(conn, attachment_ids, user_id)
    for_prompt: list[dict] = []
    for_trace: list[dict] = []

    for row in rows:
        for_trace.append(
            {
                "id": str(row["id"]),
                "file_name": row["file_name"],
                "kind": row["kind"],
                "extraction_status": row["extraction_status"],
            }
        )
        item = {"file_name": row["file_name"], "kind": row["kind"], "content_type": row["content_type"]}
        if row["extracted_text"]:
            item["content"] = row["extracted_text"]
            if row["truncated_chars"]:
                item["note"] = f"Conteúdo cortado: {row['truncated_chars']} caractere(s) não incluídos."
        else:
            # Dizer ao modelo o que ele NÃO tem é tão importante quanto o que
            # tem — sem isso ele responde sobre o arquivo como se tivesse lido.
            item["content"] = None
            item["unavailable_reason"] = row["extraction_error"] or _default_reason(row["kind"])
        for_prompt.append(item)

    return for_prompt, for_trace


def transcribe_attachment_audio(content: bytes, content_type: str, file_name: str) -> dict:
    """Chama o Whisper de verdade para um anexo de áudio.

    Mesmo contrato de `attachment_text.extract`: `{status, text, error,
    truncated_chars}`. Nunca levanta — sem `OPENAI_API_KEY` ou com a API do
    provedor fora do ar, o anexo continua sendo salvo, só fica marcado como
    não transcrito. Um anexo de áudio que falha ao subir seria pior que um
    anexo salvo sem o conteúdo falado.
    """
    try:
        result = transcribe_audio_safe(content, file_name, content_type)
    except Exception as exc:  # noqa: BLE001 — motivo no docstring acima
        return {"status": "failed", "text": None, "error": str(exc)[:500], "truncated_chars": None}

    text = (result.get("text") or "").strip()
    if not text:
        return {
            "status": "unsupported",
            "text": None,
            "error": "Transcrição vazia — o áudio não tinha fala reconhecível.",
            "truncated_chars": None,
        }
    if len(text) > attachment_text.MAX_CHARS:
        return {
            "status": "extracted",
            "text": text[: attachment_text.MAX_CHARS],
            "error": None,
            "truncated_chars": len(text) - attachment_text.MAX_CHARS,
        }
    return {"status": "extracted", "text": text, "error": None, "truncated_chars": 0}


def _default_reason(kind: str) -> str:
    if kind == "image":
        return (
            "Imagem: o conteúdo visual só é lido por um modelo com visão. "
            "Descreva o que importa na imagem se a resposta depender dela."
        )
    if kind == "audio":
        return (
            "Áudio: a transcrição não foi possível. "
            "O arquivo está guardado, mas o conteúdo falado não foi lido."
        )
    return "Conteúdo não pôde ser extraído."


def _summary(row: dict) -> CopilotAttachment:
    return CopilotAttachment(
        id=row["id"],
        thread_id=row["thread_id"],
        file_name=row["file_name"],
        content_type=row["content_type"],
        size_bytes=row["size_bytes"],
        kind=row["kind"],
        extraction_status=row["extraction_status"],
        extraction_error=row["extraction_error"],
        truncated_chars=row["truncated_chars"],
        has_text=bool(row["extracted_text"]),
        created_at=row["created_at"],
    )


def _safe_filename(file_name: str) -> str:
    return "".join(char if char.isalnum() or char in "-_." else "-" for char in file_name)[:120]
