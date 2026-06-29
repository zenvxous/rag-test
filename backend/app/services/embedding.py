import httpx
from core.exceptions import (
    EmbeddingConnectionError,
    EmbeddingDimMismatchError,
    EmbeddingTimeoutError,
    EmbeddingValidationError,
)

from app.core.dependencies import settings
from app.db.constants import embedding_dim


async def embed_text(text: str, client: httpx.AsyncClient) -> list[float]:
    if text is None or not text.split():
        raise EmbeddingValidationError("Input text must not be empty")

    try:
        response = await client.post(
            url=f"{settings.ollama_base_url}/api/embed",
            json={
                "model": settings.embedding_model,
                "input": text,
            },
        )
        response.raise_for_status()
    except httpx.TimeoutException as e:
        raise EmbeddingTimeoutError("Request to embedding service timed out") from e
    except httpx.HTTPStatusError as e:
        raise EmbeddingConnectionError(
            f"Embedding service returned {e.response.status_code}: {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise EmbeddingConnectionError(f"Failed to reach embedding service: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise EmbeddingConnectionError("Embedding service returned invalid JSON") from e

    if data.get("model") != settings.embedding_model:
        raise EmbeddingConnectionError(
            f"Expected model '{settings.embedding_model}', got '{data.get('model')}'"
        )

    embedding = data.get("embeddings")[0]
    if not isinstance(embedding, list):
        raise EmbeddingValidationError("Response does not contain a valid embedding")

    if len(embedding) != embedding_dim:
        raise EmbeddingDimMismatchError(
            f"Expected {embedding_dim}, got {len(embedding)}"
        )

    return embedding

async def embed_texts(texts: list[str], client: httpx.AsyncClient) -> list[list[float]]:
    if not texts or any(text is None or not text.split() for text in texts):
        raise EmbeddingValidationError("Input texts must not be empty")

    try:
        response = await client.post(
            url=f"{settings.ollama_base_url}/api/embed",
            json={
                "model": settings.embedding_model,
                "input": texts,
            },
        )
        response.raise_for_status()
    except httpx.TimeoutException as e:
        raise EmbeddingTimeoutError("Request to embedding service timed out") from e
    except httpx.HTTPStatusError as e:
        raise EmbeddingConnectionError(
            f"Embedding service returned {e.response.status_code}: {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise EmbeddingConnectionError(f"Failed to reach embedding service: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise EmbeddingConnectionError("Embedding service returned invalid JSON") from e

    embeddings = data.get("embeddings")
    if not isinstance(embeddings, list) or not all(
        isinstance(embed, list) for embed in embeddings
    ):
        raise EmbeddingValidationError("Response does not contain valid embeddings")

    for embed in embeddings:
        if len(embed) != embedding_dim:
            raise EmbeddingDimMismatchError(
                f"Expected {embedding_dim}, got {len(embed)}"
            )

    return embeddings
