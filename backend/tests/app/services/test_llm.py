from __future__ import annotations

from typing import Any, cast

import httpx
import pytest

import app.services.llm as llm_service
from app.exceptions.llm import LLMConnectionError, LLMResponseError, LLMTimeoutError


class DummyResponse:
    def __init__(self, *, status_code: int = 200, body: bytes = b"", lines: list[str] | None = None) -> None:
        self.status_code = status_code
        self._body = body
        self._lines = lines or []

    async def aread(self) -> bytes:
        return self._body

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class DummyStreamContext:
    def __init__(self, response: DummyResponse | None = None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc

    async def __aenter__(self) -> DummyResponse:
        if self._exc is not None:
            raise self._exc
        if self._response is None:
            raise AssertionError("response is required")
        return self._response

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


class DummyClient:
    def __init__(self, response: DummyResponse | None = None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc

    def stream(self, method: str, url: str, json: dict[str, Any]) -> DummyStreamContext:
        return DummyStreamContext(self._response, self._exc)


@pytest.fixture(autouse=True)
def configure_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_service.settings, "llm_model", "test-model")
    monkeypatch.setattr(llm_service.settings, "llm_context_length", 2048)
    monkeypatch.setattr(llm_service.settings, "llm_temperature", 0.2)
    monkeypatch.setattr(llm_service.settings, "ollama_base_url", "http://ollama")
    monkeypatch.setattr(llm_service.settings, "http_timeout", 30)


def test_build_payload_uses_current_settings() -> None:
    payload = llm_service._build_payload("hello")

    assert payload == {
        "model": "test-model",
        "prompt": "hello",
        "stream": True,
        "options": {
            "num_ctx": 2048,
            "temperature": 0.2,
        },
    }


@pytest.mark.asyncio
async def test_generate_stream_yields_tokens_and_stops_on_done() -> None:
    client = DummyClient(
        response=DummyResponse(
            lines=[
                "",
                "not-json",
                '{"response": "Hello"}',
                '{"response": " world"}',
                '{"response": "!", "done": true}',
            ]
        )
    )

    tokens = [token async for token in llm_service.generate_stream("hello", cast(httpx.AsyncClient, client))]

    assert tokens == ["Hello", " world", "!"]


@pytest.mark.asyncio
async def test_generate_stream_raises_response_error_for_non_200() -> None:
    client = DummyClient(response=DummyResponse(status_code=500, body=b"bad gateway"))

    with pytest.raises(LLMResponseError) as exc_info:
        async for _ in llm_service.generate_stream("hello", cast(httpx.AsyncClient, client)):
            pass

    assert exc_info.value.status_code == 500
    assert "bad gateway" in exc_info.value.detail


@pytest.mark.asyncio
async def test_generate_stream_wraps_connect_errors() -> None:
    client = DummyClient(exc=httpx.ConnectError("boom"))

    with pytest.raises(LLMConnectionError, match="Cannot connect"):
        async for _ in llm_service.generate_stream("hello", cast(httpx.AsyncClient, client)):
            pass


@pytest.mark.asyncio
async def test_generate_stream_wraps_timeouts() -> None:
    client = DummyClient(exc=httpx.ReadTimeout("slow"))

    with pytest.raises(LLMTimeoutError, match="timed out"):
        async for _ in llm_service.generate_stream("hello", cast(httpx.AsyncClient, client)):
            pass


@pytest.mark.asyncio
async def test_generate_stream_wraps_generic_http_errors() -> None:
    client = DummyClient(exc=httpx.HTTPError("unexpected"))

    with pytest.raises(LLMConnectionError, match="Unexpected HTTP error"):
        async for _ in llm_service.generate_stream("hello", cast(httpx.AsyncClient, client)):
            pass
