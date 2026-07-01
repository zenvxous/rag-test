from fastapi import HTTPException


class FailedToParsePDFError(HTTPException):
    def __init__(self, detail: str = "Failed to parse PDF"):
        super().__init__(status_code=500, detail=detail)

class InvalidChunkPayloadError(HTTPException):
    def __init__(self, detail: str = "Invalid chunk payload"):
        super().__init__(status_code=400, detail=detail)

class NoChunksProducedError(HTTPException):
    def __init__(self, detail: str = "No chunks were produced from the document"):
        super().__init__(status_code=500, detail=detail)

class EmbeddingCountMismatchError(HTTPException):
    def __init__(self, expected: int, got: int):
        detail = f"Embedding count mismatch: expected {expected}, got {got}"
        super().__init__(status_code=500, detail=detail)

class MissingEmbeddingError(HTTPException):
    def __init__(self, chunk_index: int):
        detail = f"Chunk {chunk_index} has no embedding."
        super().__init__(status_code=500, detail=detail)
