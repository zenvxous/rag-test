from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.ingestion import ChunkPayload


@pytest.fixture
def sample_document_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def sample_filename() -> str:
    return "sample.pdf"


@pytest.fixture
def sample_bytes() -> bytes:
    return b"%PDF-1.4\n%test"


@pytest.fixture
def fake_session() -> Mock:
    session = Mock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add_all = Mock()
    return session


@pytest.fixture
def fake_s3_client() -> Mock:
    return Mock()


@pytest.fixture
def fake_http_client() -> Mock:
    return Mock()


@pytest.fixture
def sample_chunk_payloads(sample_document_id: uuid.UUID) -> list[ChunkPayload]:
    return [
        ChunkPayload(
            document_id=sample_document_id,
            chunk_index=0,
            content="First chunk content",
            page_number=1,
            token_count=3,
        ),
        ChunkPayload(
            document_id=sample_document_id,
            chunk_index=1,
            content="Second chunk content",
            page_number=2,
            token_count=3,
        ),
    ]
