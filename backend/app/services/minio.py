from botocore.exceptions import BotoCoreError, ClientError

from app.core.dependencies import settings
from app.exceptions.minio import (
    MinIOAccessDeniedError,
    MinIOBucketNotFoundError,
    MinIOObjectConflictError,
    MinIOStorageUnavailableError,
    MinIOUnknownError,
    MinIOUploadValidationError,
)


async def upload_pdf(file_bytes: bytes, object_key: str, s3_client) -> str:
    if not file_bytes:
        raise MinIOUploadValidationError("PDF file bytes are empty")

    if not object_key or not object_key.strip():
        raise MinIOUploadValidationError("object_key is empty")

    try:
        response = await s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
            Body=file_bytes,
            ContentType="application/pdf",
        )

        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code not in (200, 201):
            raise MinIOStorageUnavailableError(
                f"Unexpected S3 response status: {status_code}"
            )

        return object_key

    except ClientError as e:
        error = e.response.get("Error", {})
        code = error.get("Code", "")
        message = error.get("Message", str(e))

        if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            raise MinIOAccessDeniedError(message) from e

        if code in {"NoSuchBucket"}:
            raise MinIOBucketNotFoundError(message) from e

        if code in {
            "BucketAlreadyExists",
            "BucketAlreadyOwnedByYou",
            "OperationAborted",
        }:
            raise MinIOObjectConflictError(message) from e

        if code in {
            "RequestTimeout",
            "SlowDown",
            "InternalError",
            "ServiceUnavailable",
        }:
            raise MinIOStorageUnavailableError(message) from e

        raise MinIOUnknownError(f"{code}: {message}") from e

    except BotoCoreError as e:
        raise MinIOStorageUnavailableError(str(e)) from e

    except Exception as e:
        raise MinIOUnknownError(str(e)) from e

async def download_pdf(object_key: str, s3_client) -> bytes:
    if not object_key or not object_key.strip():
        raise MinIOUploadValidationError("object_key is empty")

    try:
        response = await s3_client.get_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
        )
        file_bytes = await response["Body"].read()
        return file_bytes

    except ClientError as e:
        error = e.response.get("Error", {})
        code = error.get("Code", "")
        message = error.get("Message", str(e))

        if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            raise MinIOAccessDeniedError(message) from e

        if code in {"NoSuchBucket", "NoSuchKey"}:
            raise MinIOBucketNotFoundError(message) from e

        if code in {
            "RequestTimeout",
            "SlowDown",
            "InternalError",
            "ServiceUnavailable",
        }:
            raise MinIOStorageUnavailableError(message) from e

        raise MinIOUnknownError(f"{code}: {message}") from e

    except BotoCoreError as e:
        raise MinIOStorageUnavailableError(str(e)) from e

    except Exception as e:
        raise MinIOUnknownError(str(e)) from e

async def generate_presigned_url(object_key: str, expires_int: int, s3_clinet):
    if not object_key or not object_key.strip():
        raise MinIOUploadValidationError("object_key is empty")

    try:
        presigned_url = await s3_clinet.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": object_key},
            ExpiresIn=expires_int,
        )
        return presigned_url

    except ClientError as e:
        error = e.response.get("Error", {})
        code = error.get("Code", "")
        message = error.get("Message", str(e))

        if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            raise MinIOAccessDeniedError(message) from e

        if code in {"NoSuchBucket", "NoSuchKey"}:
            raise MinIOBucketNotFoundError(message) from e

        if code in {
            "RequestTimeout",
            "SlowDown",
            "InternalError",
            "ServiceUnavailable",
        }:
            raise MinIOStorageUnavailableError(message) from e

        raise MinIOUnknownError(f"{code}: {message}") from e

    except BotoCoreError as e:
        raise MinIOStorageUnavailableError(str(e)) from e

    except Exception as e:
        raise MinIOUnknownError(str(e)) from e

async def delete_pdf(object_key: str, s3_client) -> None:
    if not object_key or not object_key.strip():
        raise MinIOUploadValidationError("object_key is empty")

    try:
        await s3_client.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
        )

    except ClientError as e:
        error = e.response.get("Error", {})
        code = error.get("Code", "")
        message = error.get("Message", str(e))

        if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            raise MinIOAccessDeniedError(message) from e

        if code in {"NoSuchBucket", "NoSuchKey"}:
            raise MinIOBucketNotFoundError(message) from e

        if code in {
            "RequestTimeout",
            "SlowDown",
            "InternalError",
            "ServiceUnavailable",
        }:
            raise MinIOStorageUnavailableError(message) from e

        raise MinIOUnknownError(f"{code}: {message}") from e

    except BotoCoreError as e:
        raise MinIOStorageUnavailableError(str(e)) from e

    except Exception as e:
        raise MinIOUnknownError(str(e)) from e
