import logging
from uuid import UUID

import boto3

from app.config import Settings
from app.exceptions import StorageError
from app.services.file_validator import sanitize_filename

logger = logging.getLogger(__name__)


def get_upload_client(settings: Settings):
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT_URL,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    )


def get_presign_client(settings: Settings):
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_PUBLIC_URL,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    )


def ensure_bucket(s3, bucket: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        try:
            s3.create_bucket(Bucket=bucket)
        except Exception as exc:
            raise StorageError(f"Could not ensure bucket {bucket!r}: {exc}") from exc


def upload_resume(
    s3,
    bucket: str,
    lead_id: UUID,
    filename: str,
    data: bytes,
    content_type: str,
) -> str:
    safe_name = sanitize_filename(filename)
    key = f"{lead_id}/{safe_name}"
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    except Exception as exc:
        raise StorageError(f"Upload failed: {exc}") from exc
    return key


def delete_object(s3, bucket: str, path: str) -> None:
    try:
        s3.delete_object(Bucket=bucket, Key=path)
    except Exception as exc:
        logger.warning("Failed to delete object %s: %s", path, exc)


def create_presigned_url(
    s3,
    bucket: str,
    path: str,
    expires_in_seconds: int = 3600,
) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": path},
        ExpiresIn=expires_in_seconds,
    )
