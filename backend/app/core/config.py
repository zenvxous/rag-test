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
    s3_sigrature_version: str = "s3v4"
    s3_max_pool_connections: int = 20

    ollama_base_url: str = "http://ollama:11434"
    embedding_model: str = "nomic-embed-text"
    llm_model: str = "qwen2.5:1.5b"
    llm_context_length: int = 2048
    llm_temperature: float = 0.1

    http_timeout: int = 120
    http_connect_timeout: int = 5
    http_max_connections: int = 100
    http_keepalive_connections: int = 20

    chunk_size: int = 350
    chunk_overlap: int = 50
    chunk_separators: list[str] = ["\n\n", "\n", " ", ""]
    embed_batch_size: int = 15
    top_k_chunks: int = 3

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
