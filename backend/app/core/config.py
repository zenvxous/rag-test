from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "rag-test-backend"
    app_env: str = "dev"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://raguser:ragpassword@postgres:5432/ragdb"

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin123"
    s3_bucket_name: str = "pdf-documents"
    s3_region: str = "us-east-1"

    ollama_base_url: str = "http://ollama:11434"
    llm_model: str = "qwen2.5:1.5b"
    embedding_model: str = "nomic-embed-text"
    ollama_timeout: int = 120

    chunk_size: int = 350
    chunk_overlap: int = 50
    top_k_chunks: int = 3

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

settings = Settings()
