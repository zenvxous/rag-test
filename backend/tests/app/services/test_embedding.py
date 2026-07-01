from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.db.constants import embedding_dim
from app.exceptions.embedding import EmbeddingTimeoutError, EmbeddingValidationError
from app.services import embedding as embedding_service


class DummyResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception("HTTP error")

    def json(self) -> dict:
        return self._payload


@pytest.mark.asyncio
async def test_embed_text_rejects_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding_service.settings, "ollama_base_url", "http://ollama")
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "test-model")

    with pytest.raises(EmbeddingValidationError):
        await embedding_service.embed_text("", client=AsyncMock())


@pytest.mark.asyncio
async def test_embed_text_returns_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding_service.settings, "ollama_base_url", "http://ollama")
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "test-model")

    client = AsyncMock()
    client.post.return_value = DummyResponse(
        {"model": "test-model", "embeddings": [[0.1] * embedding_dim]}
    )

    result = await embedding_service.embed_text("hello", client=client)

    assert result == [0.1] * embedding_dim


@pytest.mark.asyncio
async def test_embed_text_raises_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding_service.settings, "ollama_base_url", "http://ollama")
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "test-model")

    client = AsyncMock()
    client.post.side_effect = embedding_service.httpx.TimeoutException("timeout")

    with pytest.raises(EmbeddingTimeoutError):
        await embedding_service.embed_text("hello", client=client)


@pytest.mark.asyncio
async def test_embed_texts_returns_multiple_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding_service.settings, "ollama_base_url", "http://ollama")
    monkeypatch.setattr(embedding_service.settings, "embedding_model", "test-model")

    client = AsyncMock()
    client.post.return_value = DummyResponse(
        {"embeddings": [[0.2] * embedding_dim, [0.3] * embedding_dim]}
    )

    result = await embedding_service.embed_texts(["hello", "world"], client=client)

    assert len(result) == 2
    assert result[0] == [0.2] * embedding_dim
