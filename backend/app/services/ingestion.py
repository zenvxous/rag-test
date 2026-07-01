import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pymupdf
import pymupdf4llm
from langchain_core.documents import Document as LangchainDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import settings
from app.db.models.document_chunks import DocumentChunk
from app.db.models.documents import Document, Status
from app.exceptions.ingestion import (
    EmbeddingCountMismatchError,
    FailedToParsePDFError,
    InvalidChunkPayloadError,
    MissingEmbeddingError,
    NoChunksProducedError,
)
from app.services import embedding as embedding_service
from app.services.minio import upload_pdf


@dataclass(slots=True)
class ChunkPayload:
    document_id: UUID
    chunk_index: int
    content: str
    page_number: int
    token_count: int
    embedding: list[float] | None = field(default=None)

    def __post_init__(self) -> None:
        if not self.content:
            raise InvalidChunkPayloadError("ChunkPayload.content cannot be empty")
        if self.chunk_index < 0:
            raise InvalidChunkPayloadError("ChunkPayload.chunk_index must be >= 0")
        if self.page_number < 1:
            raise InvalidChunkPayloadError("ChunkPayload.page_number must be >= 1")

def _estimate_token_count(text: str) -> int:
    return len(text.split())

async def _upload_to_minio(
    document_id: UUID,
    filename: str,
    file_bytes: bytes,
    s3_client: Any,
) -> str:
    object_key = f"documents/{document_id}/{filename}"
    await upload_pdf(file_bytes, object_key, s3_client)
    return object_key

def _parse_pdf(file_bytes: bytes) -> list[dict]:
    try:
        with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
            pages = pymupdf4llm.to_markdown(doc, page_chunks=True)
    except Exception as e:
        raise FailedToParsePDFError(
            f"PyMuPDF4LLM failed to parse PDF: {e}"
        ) from e

    if isinstance(pages, str):
        raise FailedToParsePDFError("Failed to parse PDF into pages")
    if not pages:
        raise FailedToParsePDFError("PDF contains no extractable text")

    return pages

def _split_chunks(
    pages: list[dict[str, Any]],
    document_id: UUID,
    filename: str,
) -> list[ChunkPayload]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=settings.chunk_separators,
        length_function=len,
        is_separator_regex=False,
    )

    source_documents: list[LangchainDocument] = []

    for page_idx, page in enumerate(pages):
        text = (page.get("text") or "").strip()
        page_meta = page.get("metadata") or {}

        if not text:
            continue

        page_number = page_meta.get("page", page_idx) + 1

        source_documents.append(
            LangchainDocument(
                page_content=text,
                metadata={
                    "document_id": str(document_id),
                    "filename": filename,
                    "page_number": page_number,
                },
            )
        )

    if not source_documents:
        raise NoChunksProducedError(
            f"All pages were empty after parsing. document_id={document_id}"
        )

    split_docs = splitter.split_documents(source_documents)

    chunks: list[ChunkPayload] = []
    chunk_index = 0


    for doc in split_docs:
        chunk_text = doc.page_content.strip()
        if not chunk_text:
            continue

        chunks.append(
            ChunkPayload(
                document_id=document_id,
                chunk_index=chunk_index,
                content=chunk_text,
                page_number=doc.metadata["page_number"],
                token_count=_estimate_token_count(chunk_text),
            )
        )
        chunk_index += 1

    if not chunks:
        raise NoChunksProducedError(
            f"Splitter produced zero non-empty chunks. document_id={document_id}"
        )

    return chunks

async def _embed_chunks(
    chunks: list[ChunkPayload],
    client: httpx.AsyncClient,
) -> list[ChunkPayload]:
    if not chunks:
        return chunks

    for start in range(0, len(chunks), settings.embed_batch_size):
        batch = chunks[start : start + settings.embed_batch_size]
        texts = [chunk.content for chunk in batch]

        embeddings = await embedding_service.embed_texts(texts, client=client)

        if len(embeddings) != len(batch):
            raise EmbeddingCountMismatchError(
                expected=len(batch),
                got=len(embeddings),
            )

        for chunk, embedding in zip(batch, embeddings, strict=True):
            chunk.embedding = embedding

    return chunks

async def _save_chunks(chunks: list[ChunkPayload], session: AsyncSession) -> None:
    if not chunks:
        return

    db_chunks: list[DocumentChunk] = []

    for chunk in chunks:
        if chunk.embedding is None:
            raise MissingEmbeddingError(chunk.chunk_index)

        db_chunks.append(
            DocumentChunk(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                token_count=chunk.token_count,
                embedding=chunk.embedding,
            )
        )

    session.add_all(db_chunks)
    await session.flush()

async def ingest_document(
    document_id: UUID,
    filename: str,
    file_bytes: bytes,
    session: AsyncSession,
    client: httpx.AsyncClient,
    s3_client: Any,
) -> None:
    try:
        object_key = await _upload_to_minio(document_id, filename, file_bytes, s3_client)

        await session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(minio_key=object_key, status=Status.PROCESSING)
        )
        await session.flush()

        pages = await asyncio.to_thread(_parse_pdf, file_bytes)
        chunks = await asyncio.to_thread(_split_chunks, pages, document_id, filename)
        chunks = await _embed_chunks(chunks, client)
        await _save_chunks(chunks, session)

        await session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                status=Status.INDEXED,
                indexed_at=datetime.now(UTC),
            )
        )
        await session.commit()
    except Exception as e:
        await session.rollback()
        try:
            await session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    status=Status.ERROR,
                    error_message=f"{type(e).__name__}: {str(e)}"[:1000],
                )
            )
            await session.commit()
        except Exception:
            pass
        raise
