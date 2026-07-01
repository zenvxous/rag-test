from fastapi import HTTPException


class MinIOUploadValidationError(HTTPException):
    def __init__(self, detail: str = "Invalid MinIO upload payload"):
        super().__init__(status_code=400, detail=detail)

class MinIOAccessDeniedError(HTTPException):
    def __init__(self, detail: str = "Access denied for MinIO object upload"):
        super().__init__(status_code=403, detail=detail)

class MinIOBucketNotFoundError(HTTPException):
    def __init__(self, detail: str = "MinIO bucket not found"):
        super().__init__(status_code=404, detail=detail)

class MinIOObjectConflictError(HTTPException):
    def __init__(self, detail: str = "MinIO object conflict"):
        super().__init__(status_code=409, detail=detail)

class MinIOStorageUnavailableError(HTTPException):
    def __init__(self, detail: str = "MinIO storage is temporarily unavailable"):
        super().__init__(status_code=503, detail=detail)

class MinIOUnknownError(HTTPException):
    def __init__(self, detail: str = "Unexpected MinIO error"):
        super().__init__(status_code=500, detail=detail)
