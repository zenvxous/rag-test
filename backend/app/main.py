from contextlib import asynccontextmanager

import aioboto3
import httpx
from botocore.config import Config as BotoConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.core.dependencies import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            settings.http_timeout,
            connect=settings.http_connect_timeout,
        ),
        limits=httpx.Limits(
            max_connections=settings.http_max_connections,
            max_keepalive_connections=settings.http_keepalive_connections,
        ),
    )

    session = aioboto3.Session(
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )
    s3_ctx = session.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        config=BotoConfig(
            signature_version=settings.s3_sigrature_version,
            max_pool_connections=settings.s3_max_pool_connections,
        )
    )
    app.state.s3_client = await s3_ctx.__aenter__()
    app.state.s3_client_ctx = s3_ctx

    yield

    await app.state.http_client.aclose()
    await app.state.s3_client_ctx.__aexit__(None, None, None)

app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
