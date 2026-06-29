import asyncio
import time
from http import HTTPStatus

import httpx
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_http_client, get_s3_client, settings
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
async def liveness_check():
    payload = {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }

    return payload

async def check_database(session: AsyncSession) -> dict:
    started = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as e:
        return {
            "status": "error",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "detail": str(e),
        }

async def check_minio(s3_client) -> dict:
    started = time.perf_counter()
    try:
        buckets = await s3_client.list_buckets()
        bucket_names = [bucket["Name"] for bucket in buckets.get("Buckets", [])]

        if settings.s3_bucket_name not in bucket_names:
            return {
                "status": "error",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "detail": f"Bucket '{settings.s3_bucket_name}' not found",
            }

        return {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "bucket": settings.s3_bucket_name,
        }

    except (BotoCoreError, ClientError, Exception) as e:
        return {
            "status": "error",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "detail": str(e),
        }

async def check_ollama(http_client: httpx.AsyncClient) -> dict:
    started = time.perf_counter()
    try:
        response = await http_client.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=5.0,
        )
        response.raise_for_status()
        data = response.json()

        model_names = [model["name"] for model in data.get("models", [])]

        missing_models = []
        if settings.llm_model not in model_names:
            missing_models.append(settings.llm_model)
        if settings.embedding_model not in model_names:
            missing_models.append(settings.embedding_model)

        if missing_models:
            return {
                "status": "error",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "detail": f"Missing models: {', '.join(missing_models)}",
            }

        return {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
        }

    except Exception as e:
        return {
            "status": "error",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "detail": str(e),
        }

@router.get("/ready")
async def readiness_check(
    session: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    s3_client = Depends(get_s3_client),
):
    db_result, minio_result, ollama_result = await asyncio.gather(
        check_database(session=session),
        check_minio(s3_client=s3_client),
        check_ollama(http_client=http_client),
    )
    checks = {
        "database": db_result,
        "minio": minio_result,
        "ollama": ollama_result,
    }

    overall_status = "ok"
    http_status = HTTPStatus.OK

    if any(service["status"] != "ok" for service in checks.values()):
        overall_status = "error"
        http_status = HTTPStatus.SERVICE_UNAVAILABLE

    payload = {
        "status": overall_status,
        "service": settings.app_name,
        "environment": settings.app_env,
        "checks": checks,
    }

    if http_status != HTTPStatus.OK:
        raise HTTPException(status_code=http_status, detail=payload)

    return payload
