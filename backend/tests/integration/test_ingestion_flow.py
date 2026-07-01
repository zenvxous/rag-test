from __future__ import annotations

import uuid
from typing import cast
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.ingestion as ingestion_service


@pytest.mark.asyncio
async def test_ingestion_flow_uses_service_layers(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    session = Mock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add_all = Mock()

    async def fake_upload(document_id: uuid.UUID, filename: str, file_bytes: bytes, s3_client: object) -> str:
        return f"documents/{document_id}/{filename}"

    monkeypatch.setattr(ingestion_service, "_upload_to_minio", fake_upload)
    monkeypatch.setattr(ingestion_service, "_parse_pdf", lambda file_bytes: [{"text": "hello world", "metadata": {"page": 0}}])
    monkeypatch.setattr(ingestion_service, "_split_chunks", lambda pages, document_id, filename: [
        ingestion_service.ChunkPayload(
            document_id=document_id,
            chunk_index=0,
            content="hello world",
            page_number=1,
            token_count=2,
        )
    ])
    async def fake_embed_chunks(chunks: list[ingestion_service.ChunkPayload], client: object) -> list[ingestion_service.ChunkPayload]:
        return [
            ingestion_service.ChunkPayload(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                token_count=chunk.token_count,
                embedding=[0.1, 0.2, 0.3],
            )
            for chunk in chunks
        ]

    monkeypatch.setattr(ingestion_service, "_embed_chunks", fake_embed_chunks)
    monkeypatch.setattr(ingestion_service, "_save_chunks", AsyncMock())

    client = cast(httpx.AsyncClient, AsyncMock())
    await ingestion_service.ingest_document(
        document_id=document_id,
        filename="demo.pdf",
        file_bytes=b"pdf",
        session=cast(AsyncSession, session),
        client=client,
        s3_client=object(),
    )

    assert session.commit.await_count == 1
    assert session.rollback.await_count == 0
