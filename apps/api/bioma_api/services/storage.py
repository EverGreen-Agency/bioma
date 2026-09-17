from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from bioma_api.config import get_settings


class StorageNotConfiguredError(Exception):
    pass


class StorageOperationError(Exception):
    pass


@lru_cache
def _client():
    settings = get_settings()
    if not settings.storage_configured:
        raise StorageNotConfiguredError("Armazenamento de arquivos não configurado neste ambiente.")

    return boto3.client(
        "s3",
        region_name=settings.storage_s3_region,
        endpoint_url=settings.storage_s3_endpoint_url,
        aws_access_key_id=settings.storage_s3_access_key_id,
        aws_secret_access_key=settings.storage_s3_secret_access_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.storage_s3_force_path_style else "auto"},
        ),
    )


def put_object(key: str, body: bytes, content_type: str) -> None:
    settings = get_settings()
    try:
        _client().put_object(Bucket=settings.storage_s3_bucket, Key=key, Body=body, ContentType=content_type)
    except (BotoCoreError, ClientError) as error:
        raise StorageOperationError(f"Falha ao enviar arquivo para o armazenamento: {error}") from error


def delete_object(key: str) -> None:
    settings = get_settings()
    try:
        _client().delete_object(Bucket=settings.storage_s3_bucket, Key=key)
    except (BotoCoreError, ClientError) as error:
        raise StorageOperationError(f"Falha ao remover arquivo do armazenamento: {error}") from error


def presigned_get_url(key: str, expires_in: int = 300) -> str:
    settings = get_settings()
    try:
        return _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.storage_s3_bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as error:
        raise StorageOperationError(f"Falha ao gerar link de download: {error}") from error
