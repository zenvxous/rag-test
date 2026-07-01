from __future__ import annotations

import uuid
from typing import Any, cast
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.ingestion as ingestion_service
from app.exceptions.ingestion import (
    EmbeddingCountMismatchError,
    FailedToParsePDFError,
    MissingEmbeddingError,
    NoChunksProducedError,
)


def test_chunk_payload_validation_rejects_empty_content() -> None:
    with pytest.raises(HTTPException, match="cannot be empty"):
        ingestion_service.ChunkPayload(
            document_id=uuid.uuid4(),
            chunk_index=0,
            content="",
            page_number=1,
            token_count=1,
        )


def test_chunk_payload_validation_rejects_negative_chunk_index() -> None:
    with pytest.raises(HTTPException, match="chunk_index"):
        ingestion_service.ChunkPayload(
            document_id=uuid.uuid4(),
            chunk_index=-1,
            content="text",
            page_number=1,
            token_count=1,
        )


def test_parse_pdf_raises_when_parser_returns_no_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDocument:
        def __enter__(self) -> FakeDocument:
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    monkeypatch.setattr(ingestion_service.pymupdf, "open", lambda *args, **kwargs: FakeDocument())
    monkeypatch.setattr(ingestion_service.pymupdf4llm, "to_markdown", lambda *args, **kwargs: [])

    with pytest.raises(FailedToParsePDFError):
        ingestion_service._parse_pdf(b"%PDF-1.4")


def test_split_chunks_creates_payloads_with_page_numbers(sample_document_id: uuid.UUID, sample_filename: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingestion_service.settings, "chunk_size", 50)
    monkeypatch.setattr(ingestion_service.settings, "chunk_overlap", 0)
    monkeypatch.setattr(ingestion_service.settings, "chunk_separators", ["\n\n", "\n", " ", ""])

    pages = [
        {"text": "Alpha beta gamma", "metadata": {"page": 0}},
        {"text": "Delta epsilon zeta", "metadata": {"page": 1}},
    ]

    chunks = ingestion_service._split_chunks(pages, sample_document_id, sample_filename)

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2
    assert chunks[0].document_id == sample_document_id
    assert chunks[0].content.startswith("Alpha")


def test_split_chunks_raises_when_all_pages_empty(sample_document_id: uuid.UUID, sample_filename: str) -> None:
    with pytest.raises(NoChunksProducedError):
        ingestion_service._split_chunks([{"text": "", "metadata": {"page": 0}}], sample_document_id, sample_filename)


@pytest.mark.asyncio
async def test_embed_chunks_assigns_embeddings(sample_document_id: uuid.UUID, monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [
        ingestion_service.ChunkPayload(
            document_id=sample_document_id,
            chunk_index=0,
            content="first",
            page_number=1,
            token_count=1,
        )
    ]

    async def fake_embed_texts(texts: list[str], client: object) -> list[list[float]]:
        assert texts == ["first"]
        return [[0.1, 0.2, 0.3]]

    monkeypatch.setattr(ingestion_service.embedding_service, "embed_texts", fake_embed_texts)

    client = cast(httpx.AsyncClient, AsyncMock())
    result = await ingestion_service._embed_chunks(chunks, client=client)

    assert result[0].embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_embed_chunks_raises_on_mismatched_embedding_count(sample_document_id: uuid.UUID, monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [
        ingestion_service.ChunkPayload(
            document_id=sample_document_id,
            chunk_index=0,
            content="first",
            page_number=1,
            token_count=1,
        )
    ]

    async def fake_embed_texts(texts: list[str], client: object) -> list[list[float]]:
        return []

    monkeypatch.setattr(ingestion_service.embedding_service, "embed_texts", fake_embed_texts)

    client = cast(httpx.AsyncClient, AsyncMock())
    with pytest.raises(EmbeddingCountMismatchError):
        await ingestion_service._embed_chunks(chunks, client=client)


@pytest.mark.asyncio
async def test_save_chunks_persists_embeddings(sample_document_id: uuid.UUID, fake_session: AsyncSession) -> None:
    chunk = ingestion_service.ChunkPayload(
        document_id=sample_document_id,
        chunk_index=0,
        content="persist me",
        page_number=1,
        token_count=2,
        embedding=[0.1, 0.2, 0.3],
    )

    session = cast(Any, fake_session)
    await ingestion_service._save_chunks([chunk], cast(AsyncSession, fake_session))

    session.add_all.assert_called_once()
    created = session.add_all.call_args.args[0][0]
    assert isinstance(created, ingestion_service.DocumentChunk)
    assert created.content == "persist me"


@pytest.mark.asyncio
async def test_save_chunks_raises_when_embedding_missing(sample_document_id: uuid.UUID, fake_session: AsyncSession) -> None:
    chunk = ingestion_service.ChunkPayload(
        document_id=sample_document_id,
        chunk_index=0,
        content="missing embedding",
        page_number=1,
        token_count=2,
    )

    with pytest.raises(MissingEmbeddingError):
        await ingestion_service._save_chunks([chunk], cast(AsyncSession, fake_session))


@pytest.mark.asyncio
async def test_ingest_document_marks_document_indexed_on_success(sample_document_id: uuid.UUID, sample_filename: str, sample_bytes: bytes, fake_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_upload(document_id: uuid.UUID, filename: str, file_bytes: bytes, s3_client: object) -> str:
        return f"documents/{document_id}/{filename}"

    monkeypatch.setattr(ingestion_service, "_upload_to_minio", fake_upload)
    monkeypatch.setattr(ingestion_service, "_parse_pdf", lambda file_bytes: [{"text": "page text", "metadata": {"page": 0}}])
    monkeypatch.setattr(ingestion_service, "_split_chunks", lambda pages, document_id, filename: [
        ingestion_service.ChunkPayload(
            document_id=document_id,
            chunk_index=0,
            content="chunk content",
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
        document_id=sample_document_id,
        filename=sample_filename,
        file_bytes=sample_bytes,
        session=cast(AsyncSession, fake_session),
        client=client,
        s3_client=object(),
    )

    session = cast(Any, fake_session)
    assert session.execute.await_count == 2
    assert session.flush.await_count == 1
    assert session.commit.await_count == 1
    assert session.rollback.await_count == 0


@pytest.mark.asyncio
async def test_ingest_document_marks_document_error_on_failure(sample_document_id: uuid.UUID, sample_filename: str, sample_bytes: bytes, fake_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_upload(document_id: uuid.UUID, filename: str, file_bytes: bytes, s3_client: object) -> str:
        return f"documents/{document_id}/{filename}"

    def raise_parse_error(file_bytes: bytes) -> None:
        raise ValueError("boom")

    monkeypatch.setattr(ingestion_service, "_upload_to_minio", fake_upload)
    monkeypatch.setattr(ingestion_service, "_parse_pdf", raise_parse_error)

    client = cast(httpx.AsyncClient, AsyncMock())
    with pytest.raises(ValueError, match="boom"):
        await ingestion_service.ingest_document(
            document_id=sample_document_id,
            filename=sample_filename,
            file_bytes=sample_bytes,
            session=cast(AsyncSession, fake_session),
            client=client,
            s3_client=object(),
        )

    session = cast(Any, fake_session)
    assert session.rollback.await_count == 1
    assert session.commit.await_count == 1
    assert session.execute.await_count == 2
