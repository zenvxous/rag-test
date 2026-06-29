from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.core.config import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()
settings = get_settings()

@lru_cache
def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client
HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]

