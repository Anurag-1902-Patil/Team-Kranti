"""
Media download and MinIO upload service.

Flow:
  1. Call Meta's media-info endpoint with media_id to get the download URL
  2. Download the raw bytes (streaming, respects max_file_size limit)
  3. Upload to MinIO at a stable, content-addressed key:
       raw/{YYYY-MM-DD}/{message_id}/{filename_or_media_id}
  4. Return the MinIO object key for storage in the documents table
"""

import io
import mimetypes
import os
from datetime import date

import httpx
import structlog
from minio import Minio
from minio.error import S3Error

from backend.core.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

WHATSAPP_MEDIA_URL = "https://graph.facebook.com/v21.0"


def _get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        log.info("minio.bucket_created", bucket=bucket)


async def get_media_url(media_id: str, access_token: str) -> str:
    """
    Call GET /{media_id} to retrieve the temporary download URL.
    Returns the URL string.
    """
    url = f"{WHATSAPP_MEDIA_URL}/{media_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            url, headers={"Authorization": f"Bearer {access_token}"}
        )
        resp.raise_for_status()
        data = resp.json()
        return data["url"]


async def download_media(
    media_id: str,
    access_token: str,
    filename: str | None = None,
) -> tuple[bytes, str]:
    """
    Download media bytes from WhatsApp CDN.

    Returns:
        (bytes, mime_type)
    Raises:
        ValueError if file exceeds size limit.
    """
    download_url = await get_media_url(media_id, access_token)

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(
            download_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()

        content_length = int(resp.headers.get("content-length", 0))
        if content_length > settings.max_file_size_bytes:
            raise ValueError(
                f"File too large: {content_length} bytes "
                f"(limit: {settings.max_file_size_bytes})"
            )

        raw_bytes = resp.content
        if len(raw_bytes) > settings.max_file_size_bytes:
            raise ValueError(f"Downloaded file exceeds size limit")

        mime_type = resp.headers.get(
            "content-type", "application/octet-stream"
        ).split(";")[0].strip()

    return raw_bytes, mime_type


def upload_to_minio(
    content: bytes,
    message_id: str,
    filename: str,
    mime_type: str,
    bucket: str | None = None,
) -> str:
    """
    Upload bytes to MinIO. Returns the object key.

    Key format: raw/{date}/{message_id}/{filename}
    """
    target_bucket = bucket or settings.minio_bucket_raw
    client = _get_minio_client()
    _ensure_bucket(client, target_bucket)

    today = date.today().isoformat()
    # Sanitize filename
    safe_filename = os.path.basename(filename).replace(" ", "_") or f"{message_id}.bin"
    object_key = f"raw/{today}/{message_id}/{safe_filename}"

    client.put_object(
        bucket_name=target_bucket,
        object_name=object_key,
        data=io.BytesIO(content),
        length=len(content),
        content_type=mime_type,
    )

    log.info(
        "minio.uploaded",
        bucket=target_bucket,
        key=object_key,
        size=len(content),
        mime_type=mime_type,
    )
    return object_key


def upload_extracted_text(text: str, message_id: str, suffix: str = "extracted.txt") -> str:
    """Upload extracted text (OCR/ASR output) to the extracted bucket."""
    content = text.encode("utf-8")
    return upload_to_minio(
        content=content,
        message_id=message_id,
        filename=suffix,
        mime_type="text/plain",
        bucket=settings.minio_bucket_extracted,
    )


def get_presigned_url(object_key: str, bucket: str | None = None, expires_seconds: int = 3600) -> str:
    """Generate a presigned download URL for a MinIO object."""
    from datetime import timedelta
    client = _get_minio_client()
    target_bucket = bucket or settings.minio_bucket_raw
    return client.presigned_get_object(
        target_bucket, object_key, expires=timedelta(seconds=expires_seconds)
    )
