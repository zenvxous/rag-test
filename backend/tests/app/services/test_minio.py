from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.exceptions.minio import MinIOUnknownError, MinIOUploadValidationError
from app.services import minio as minio_service


@pytest.mark.asyncio
async def test_upload_pdf_rejects_empty_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    with pytest.raises(MinIOUploadValidationError):
        await minio_service.upload_pdf(b"", "doc.pdf", AsyncMock())


@pytest.mark.asyncio
async def test_upload_pdf_returns_object_key_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    s3_client = AsyncMock()
    s3_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    result = await minio_service.upload_pdf(b"pdf-bytes", "docs/file.pdf", s3_client)

    assert result == "docs/file.pdf"


@pytest.mark.asyncio
async def test_upload_pdf_wraps_storage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    s3_client = AsyncMock()
    s3_client.put_object.side_effect = Exception("boom")

    with pytest.raises(MinIOUnknownError, match="boom"):
        await minio_service.upload_pdf(b"pdf-bytes", "docs/file.pdf", s3_client)


@pytest.mark.asyncio
async def test_download_pdf_returns_bytes_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    s3_client = AsyncMock()
    body = AsyncMock()
    body.read.return_value = b"pdf-bytes"
    s3_client.get_object.return_value = {"Body": body}

    result = await minio_service.download_pdf("docs/file.pdf", s3_client)

    assert result == b"pdf-bytes"
    s3_client.get_object.assert_awaited_once_with(Bucket="bucket", Key="docs/file.pdf")


@pytest.mark.asyncio
async def test_download_pdf_wraps_storage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    s3_client = AsyncMock()
    s3_client.get_object.side_effect = Exception("boom")

    with pytest.raises(MinIOUnknownError, match="boom"):
        await minio_service.download_pdf("docs/file.pdf", s3_client)


@pytest.mark.asyncio
async def test_generate_presigned_url_returns_url_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    s3_client = AsyncMock()
    s3_client.generate_presigned_url.return_value = "https://example.com/presigned"

    result = await minio_service.generate_presigned_url("docs/file.pdf", 300, s3_client)

    assert result == "https://example.com/presigned"
    s3_client.generate_presigned_url.assert_awaited_once_with(
        "get_object",
        Params={"Bucket": "bucket", "Key": "docs/file.pdf"},
        ExpiresIn=300,
    )


@pytest.mark.asyncio
async def test_generate_presigned_url_wraps_storage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    s3_client = AsyncMock()
    s3_client.generate_presigned_url.side_effect = Exception("boom")

    with pytest.raises(MinIOUnknownError, match="boom"):
        await minio_service.generate_presigned_url("docs/file.pdf", 300, s3_client)


@pytest.mark.asyncio
async def test_delete_pdf_completes_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    s3_client = AsyncMock()

    await minio_service.delete_pdf("docs/file.pdf", s3_client)

    s3_client.delete_object.assert_awaited_once_with(Bucket="bucket", Key="docs/file.pdf")


@pytest.mark.asyncio
async def test_delete_pdf_wraps_storage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(minio_service.settings, "s3_bucket_name", "bucket")

    s3_client = AsyncMock()
    s3_client.delete_object.side_effect = Exception("boom")

    with pytest.raises(MinIOUnknownError, match="boom"):
        await minio_service.delete_pdf("docs/file.pdf", s3_client)
