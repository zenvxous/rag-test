import json
from collections.abc import AsyncGenerator

import httpx

from app.core.dependencies import settings
from app.exceptions.llm import LLMConnectionError, LLMResponseError, LLMTimeoutError


def _build_payload(prompt: str) -> dict:
    return {
        "model": settings.llm_model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_ctx": settings.llm_context_length,
            "temperature": settings.llm_temperature,
        },
    }

async def generate_stream(prompt: str, client: httpx.AsyncClient) -> AsyncGenerator[str]:
    url = f"{settings.ollama_base_url}/api/generate"
    payload = _build_payload(prompt)

    try:
        async with client.stream("POST", url, json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise LLMResponseError(
                    status_code=response.status_code,
                    detail=body.decode(errors="replace"),
                )
        async for line in response.aiter_lines():
            if not line:
                continue

            try:
                data = json.loads(line)
            except ValueError:
                continue

            token = data.get("response", "")
            if token:
                yield token

            if data.get("done"):
                break
    except httpx.ConnectError as e:
        raise LLMConnectionError(
            f"Cannot connect to Ollama at {settings.ollama_base_url}"
        ) from e
    except httpx.ReadTimeout as e:
        raise LLMTimeoutError(
            f"Ollama stream timed out after {settings.http_timeout}s"
        ) from e
    except httpx.HTTPError as e:
        raise LLMConnectionError(f"Unexpected HTTP error: {e}") from e
