from fastapi import HTTPException


class LLMResponseError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(
            status_code=500, detail=f"Ollama returned HTTP {status_code}: {detail}"
        )

class LLMConnectionError(HTTPException):
    def __init__(self, detail: str = "Failed to connect to Ollama"):
        super().__init__(status_code=500, detail=detail)

class LLMTimeoutError(HTTPException):
    def __init__(self, detail: str = "Ollama request timed out"):
        super().__init__(status_code=500, detail=detail)
