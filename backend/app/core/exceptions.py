from fastapi import HTTPException


class EmbeddingConnectionError(HTTPException):
    def __init__(self, detail: str = "Failed to connect to the embedding service"):
        super().__init__(status_code=503, detail=detail)

class EmbeddingDimMismatchError(HTTPException):
    def __init__(self, detail: str = "Embedding dimension mismatch"):
        super().__init__(status_code=500, detail=detail)

class EmbeddingTimeoutError(HTTPException):
    def __init__(self, detail: str = "Request to embedding service timed out"):
        super().__init__(status_code=504, detail=detail)

class EmbeddingValidationError(HTTPException):
    def __init__(self, detail: str = "Input text must not be empty"):
        super().__init__(status_code=400, detail=detail)
